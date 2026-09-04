"""Rendering di modelli 3D per la piramide olografica.

A differenza di un video 2D ripetuto quattro volte, qui ogni faccia mostra
l'oggetto ripreso da una direzione diversa: girando attorno alla piramide si
vede davvero un altro lato. E' la sola strada per avere parallasse vera.

La GPU viene toccata solo mentre si rende: il contesto OpenGL nasce quando si
crea un TurntableRenderer e muore con close(). Anche le librerie pesanti
(trimesh impiega circa cinque secondi a caricarsi) sono importate qui dentro,
quindi chi non usa modelli 3D non le paga mai.
"""

import math
import os

import numpy as np

MODEL_EXTENSIONS = (".glb", ".gltf", ".obj", ".stl", ".ply", ".off", ".dae")

# Ordine delle quattro riprese, in senso orario visto dall'alto. Corrisponde
# alle quattro regioni del canvas: chi guarda la piramide da nord vede la
# regione in alto, quindi quella regione deve contenere il lato nord.
VIEW_ORDER = ("up", "right", "down", "left")

DEFAULT_ELEVATION = 16.0
DEFAULT_FOV = 32.0

# Oltre questo angolo fra due facce lo spigolo e' considerato vivo e le
# normali non vengono mediate: e' cio' che distingue un cubo spigoloso da una
# sfera liscia senza doverlo sapere in anticipo.
CREASE_ANGLE = 40.0

# Sopra questa soglia il calcolo delle normali smussate costa piu' memoria di
# quanta ne valga la pena, e si ripiega sulle normali per faccia.
SMOOTH_FACE_LIMIT = 400_000


class ModelError(Exception):
    """Il modello non e' caricabile o non contiene geometria."""


def is_model(path):
    return os.path.splitext(path)[1].lower() in MODEL_EXTENSIONS


# ------------------------------------------------------------------ matrici

def _normalize(v):
    n = np.linalg.norm(v)
    return v / n if n else v


def look_at(eye, target, up):
    f = _normalize(np.asarray(target, "f4") - np.asarray(eye, "f4"))
    s = _normalize(np.cross(f, np.asarray(up, "f4")))
    u = np.cross(s, f)

    m = np.eye(4, dtype="f4")
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ np.asarray(eye, "f4")
    return m


def perspective(fov_deg, aspect, near, far):
    t = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    m = np.zeros((4, 4), dtype="f4")
    m[0, 0] = t / aspect
    m[1, 1] = t
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2.0 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def camera_position(azimuth_deg, elevation_deg, distance):
    """Posizione della camera attorno all'origine.

    Azimut 0 = nord (+Y), 90 = est (+X): l'ordine nord-est-sud-ovest e' orario
    visto dall'alto, lo stesso in cui si succedono le facce della piramide.
    """
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    horizontal = math.cos(el)
    return np.array([
        horizontal * math.sin(az),
        horizontal * math.cos(az),
        math.sin(el),
    ], "f4") * distance


# ------------------------------------------------------------------- shader

_VERTEX_SHADER = """
#version 330
uniform mat4 u_mvp;
uniform mat4 u_modelview;
uniform mat3 u_normal;

in vec3 in_position;
in vec3 in_normal;
in vec3 in_color;
in vec2 in_uv;

out vec3 v_position;
out vec3 v_normal;
out vec3 v_color;
out vec2 v_uv;

void main() {
    gl_Position = u_mvp * vec4(in_position, 1.0);
    v_position = (u_modelview * vec4(in_position, 1.0)).xyz;
    v_normal = u_normal * in_normal;
    v_color = in_color;
    v_uv = in_uv;
}
"""

# Luci fissate nello spazio della camera: ogni faccia della piramide riceve
# cosi' la stessa illuminazione e l'oggetto non cambia aspetto girandoci
# attorno. Il termine di bordo (rim) e' quello che rende l'aria "olografica"
# sul nero, ed e' anche cio' che il vetro riflette meglio.
_FRAGMENT_SHADER = """
#version 330
uniform float u_rim;
uniform vec3 u_rim_color;
uniform bool u_textured;
uniform sampler2D u_texture;

in vec3 v_position;
in vec3 v_normal;
in vec3 v_color;
in vec2 v_uv;

out vec4 f_color;

void main() {
    vec3 N = normalize(v_normal);
    vec3 V = normalize(-v_position);
    if (dot(N, V) < 0.0) N = -N;          // mesh con winding incoerente

    vec3 key = normalize(vec3(0.35, 0.45, 1.0));
    vec3 fill = normalize(vec3(-0.7, 0.1, 0.35));

    float diffuse = max(dot(N, key), 0.0) * 0.85
                  + max(dot(N, fill), 0.0) * 0.30;
    float rim = pow(1.0 - max(dot(N, V), 0.0), 2.5);

    vec3 base = u_textured ? texture(u_texture, v_uv).rgb * v_color : v_color;
    vec3 color = base * (0.16 + diffuse) + u_rim_color * (rim * u_rim);
    f_color = vec4(clamp(color, 0.0, 1.0), 1.0);
}
"""


# ----------------------------------------------------------------- renderer

class TurntableRenderer:
    """Rende un modello 3D da un azimut qualsiasi, su fondo nero."""

    def __init__(self, path, size=300, samples=4, fov=DEFAULT_FOV,
                 rim=0.55, rim_color=(0.45, 0.75, 1.0), base_color=None):
        # Import qui dentro: trimesh costa secondi e serve solo a chi apre un
        # modello 3D.
        import moderngl
        import trimesh

        self.size = int(size)
        self.fov = float(fov)
        self._moderngl = moderngl

        positions, normals, colors, uvs, texture = self._load(
            trimesh, path, base_color)
        self.triangles = len(positions) // 3
        self.textured = texture is not None

        self.ctx = moderngl.create_standalone_context()
        self.ctx.enable(moderngl.DEPTH_TEST)

        self.program = self.ctx.program(vertex_shader=_VERTEX_SHADER,
                                        fragment_shader=_FRAGMENT_SHADER)
        self.program["u_rim"].value = float(rim)
        self.program["u_rim_color"].value = tuple(rim_color)
        self.program["u_textured"].value = self.textured

        self.texture = None
        if texture is not None:
            self.texture = self.ctx.texture(texture[0], 3, texture[1])
            self.texture.build_mipmaps()
            self.texture.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            self.texture.repeat_x = self.texture.repeat_y = True
            self.program["u_texture"].value = 0
            self.texture.use(0)

        data = np.hstack([positions, normals, colors, uvs]).astype("f4")
        self.vbo = self.ctx.buffer(data.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, "3f 3f 3f 2f",
              "in_position", "in_normal", "in_color", "in_uv")],
        )

        self._build_targets(samples)

        # Distanza scelta perche' la sfera unitaria che racchiude il modello
        # entri sempre nell'inquadratura, con un margine.
        self.distance = 1.15 / math.sin(math.radians(self.fov) / 2.0)
        self.projection = perspective(self.fov, 1.0, 0.05, self.distance * 4.0)

    # -- costruzione

    def _load(self, trimesh, path, base_color):
        try:
            loaded = trimesh.load(path, force="mesh", process=False)
        except Exception as exc:
            raise ModelError(f"Impossibile leggere il modello: {exc}") from exc

        if hasattr(loaded, "geometry"):
            meshes = [g for g in loaded.geometry.values() if hasattr(g, "faces")]
            if not meshes:
                raise ModelError("Il file non contiene geometria.")
            loaded = trimesh.util.concatenate(meshes)

        if not hasattr(loaded, "faces") or len(loaded.faces) == 0:
            raise ModelError("Il file non contiene triangoli.")

        vertices = np.asarray(loaded.vertices, "f8")
        faces = np.asarray(loaded.faces, np.int64)

        # Centra e scala: il modello finisce dentro la sfera di raggio 1,
        # cosi' l'inquadratura non dipende dalle unita' del file.
        lo, hi = vertices.min(0), vertices.max(0)
        vertices = vertices - (lo + hi) / 2.0
        radius = float(np.linalg.norm(vertices, axis=1).max())
        if radius <= 0:
            raise ModelError("Il modello e' degenere.")
        vertices /= radius

        corners = vertices[faces].reshape(-1, 3)

        edge1 = vertices[faces[:, 1]] - vertices[faces[:, 0]]
        edge2 = vertices[faces[:, 2]] - vertices[faces[:, 0]]
        face_normals = np.cross(edge1, edge2)
        lengths = np.linalg.norm(face_normals, axis=1, keepdims=True)
        face_normals = np.divide(face_normals, np.where(lengths == 0, 1, lengths))

        normals = self._smooth_normals(loaded, faces, face_normals)
        colors = self._colors(loaded, faces, base_color)
        uvs, texture = self._texture(loaded, faces)
        return corners, normals, colors, uvs, texture

    @staticmethod
    def _smooth_normals(mesh, faces, face_normals):
        """Normali per angolo, mediate solo attraverso gli spigoli dolci.

        Mediare sempre trasforma un cubo in una bolla; non mediare mai lascia
        una sfera sfaccettata. Si media quindi soltanto fra facce che formano
        un angolo inferiore alla soglia di piega, che e' il comportamento
        atteso da chiunque abbia usato un programma di modellazione.
        """
        flat = np.repeat(face_normals, 3, axis=0)
        if len(faces) > SMOOTH_FACE_LIMIT:
            return flat

        try:
            incident = np.asarray(mesh.vertex_faces)
        except Exception:
            return flat
        if incident.ndim != 2 or incident.size == 0:
            return flat

        corner_vertex = faces.reshape(-1)
        neighbours = incident[corner_vertex]                 # (F*3, grado)
        present = neighbours >= 0

        neighbour_normals = face_normals[np.clip(neighbours, 0, None)]
        own = flat[:, None, :]

        alignment = (neighbour_normals * own).sum(-1)
        blend = present & (alignment > math.cos(math.radians(CREASE_ANGLE)))

        summed = (neighbour_normals * blend[..., None]).sum(axis=1)
        lengths = np.linalg.norm(summed, axis=1, keepdims=True)

        # Un angolo isolato non ha vicini validi: si tiene la normale piatta.
        return np.where(lengths > 1e-8, summed / np.where(lengths == 0, 1, lengths), flat)

    @staticmethod
    def _texture(mesh, faces):
        """Coordinate texture per angolo e immagine da caricare sulla GPU."""
        empty = np.zeros((faces.size, 2), "f4")

        visual = getattr(mesh, "visual", None)
        uv = getattr(visual, "uv", None)
        if uv is None:
            return empty, None

        uv = np.asarray(uv, "f8")
        if uv.shape[0] != len(mesh.vertices):
            return empty, None

        material = getattr(visual, "material", None)
        image = None
        for attribute in ("baseColorTexture", "image"):
            candidate = getattr(material, attribute, None)
            if candidate is not None:
                image = candidate
                break
        if image is None:
            return empty, None

        try:
            image = image.convert("RGB")
        except Exception:
            return empty, None

        # Due convenzioni si compensano: OpenGL conta le righe della texture
        # dal basso, mentre glTF misura la coordinata v dall'alto. Invertire
        # entrambe equivale a non invertire nulla, quindi si passano i pixel e
        # le coordinate come sono.
        pixels = np.asarray(image, np.uint8)

        corners = uv[faces].reshape(-1, 2).astype("f4")
        return corners, ((image.width, image.height), pixels.tobytes())

    @staticmethod
    def _colors(mesh, faces, base_color):
        """Colore per vertice, dal file quando c'e'."""
        count = faces.size

        if base_color is None:
            visual = getattr(mesh, "visual", None)
            try:
                vertex_colors = np.asarray(visual.vertex_colors)[:, :3] / 255.0
                if len(vertex_colors) == len(mesh.vertices) and vertex_colors.std() > 0.01:
                    return vertex_colors[faces].reshape(-1, 3).astype("f4")
            except Exception:
                pass

            try:
                factor = np.asarray(visual.material.baseColorFactor, "f8")[:3] / 255.0
                if factor.max() > 0:
                    base_color = tuple(factor)
            except Exception:
                pass

        if base_color is None:
            base_color = (0.72, 0.78, 0.86)

        return np.tile(np.asarray(base_color, "f4"), (count, 1))

    def _build_targets(self, samples):
        ctx = self.ctx
        size = (self.size, self.size)

        samples = min(int(samples), ctx.max_samples)
        if samples > 1:
            self._msaa = ctx.framebuffer(
                color_attachments=[ctx.renderbuffer(size, samples=samples)],
                depth_attachment=ctx.depth_renderbuffer(size, samples=samples),
            )
        else:
            self._msaa = None

        self._resolved = ctx.framebuffer(
            color_attachments=[ctx.renderbuffer(size)],
            depth_attachment=ctx.depth_renderbuffer(size),
        )

    # -- rendering

    def render(self, azimuth_deg, elevation_deg=DEFAULT_ELEVATION):
        """Un fotogramma dell'oggetto visto da quell'azimut, in BGR."""
        eye = camera_position(azimuth_deg, elevation_deg, self.distance)
        modelview = look_at(eye, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        mvp = self.projection @ modelview

        self.program["u_mvp"].write(np.ascontiguousarray(mvp.T, "f4"))
        self.program["u_modelview"].write(np.ascontiguousarray(modelview.T, "f4"))
        self.program["u_normal"].write(
            np.ascontiguousarray(np.linalg.inv(modelview[:3, :3]), "f4"))

        target = self._msaa or self._resolved
        target.use()
        target.clear(0.0, 0.0, 0.0, 1.0)
        self.vao.render()

        if self._msaa is not None:
            self.ctx.copy_framebuffer(self._resolved, self._msaa)

        raw = self._resolved.read(components=3)
        image = np.frombuffer(raw, np.uint8).reshape(self.size, self.size, 3)

        # OpenGL restituisce le righe dal basso e i canali in RGB.
        return np.ascontiguousarray(image[::-1, :, ::-1])

    def render_views(self, turn_deg=0.0, elevation_deg=DEFAULT_ELEVATION):
        """Le quattro riprese a 90 gradi, nell'ordine di VIEW_ORDER."""
        return {
            name: self.render(turn_deg + 90.0 * i, elevation_deg)
            for i, name in enumerate(VIEW_ORDER)
        }

    # -- ciclo di vita

    def close(self):
        """Libera la GPU. Dopo questa chiamata l'oggetto non e' piu' usabile."""
        for attribute in ("vao", "vbo", "texture", "_msaa", "_resolved", "program"):
            resource = getattr(self, attribute, None)
            if resource is not None:
                try:
                    resource.release()
                except Exception:
                    pass
            setattr(self, attribute, None)

        ctx = getattr(self, "ctx", None)
        if ctx is not None:
            try:
                ctx.release()
            except Exception:
                pass
            self.ctx = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
