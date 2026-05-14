#!/usr/bin/env python3
"""
Generate a "you must be MID to ride" height-marker pylon as a USDZ.

The post is physically 5'6" (1.6764 m) so the presenter stands a hair taller
than it in real life, but the banner advertises 5'7" — the gag. Foot tick
rings sit at real 1'–5' positions, hot-red "you are here" disk and side
pointer sit at the top of the post, double-sided MID banner above on a stem.

Output: public/pylon.usdz (served at /demo2)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, UsdUtils


HOT = (255, 61, 46)
PAPER = (254, 249, 236)
INK = (13, 13, 13)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


def make_banner_texture(out_path: Path, w: int = 1024, h: int = 512) -> None:
    img = Image.new("RGB", (w, h), HOT)
    draw = ImageDraw.Draw(img)

    big = ImageFont.truetype(FONT_BOLD, 260)
    sub = ImageFont.truetype(FONT_BOLD, 56)

    cx = w / 2
    # Title block centered around y=180; underline at y=340; subtitle at y=415.
    draw.text((cx, 180), "MID", fill=PAPER, font=big, anchor="mm")

    title_bbox = draw.textbbox((cx, 180), "MID", font=big, anchor="mm")
    underline_w = int((title_bbox[2] - title_bbox[0]) * 1.08)
    underline_h = 10
    ux = int(cx - underline_w / 2)
    uy = 338
    draw.rectangle([ux, uy, ux + underline_w, uy + underline_h], fill=PAPER)

    draw.text((cx, 418), "5'7\" — YOU ARE HERE",
              fill=PAPER, font=sub, anchor="mm")

    img.save(out_path, "PNG", optimize=True)


def add_material(stage: Usd.Stage, path: str, color: tuple, roughness: float = 0.75) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, path + "/Surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateOutput("surface", Sdf.ValueTypeNames.Token)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def add_textured_material(stage: Usd.Stage, path: str, tex_rel: str) -> UsdShade.Material:
    mat = UsdShade.Material.Define(stage, path)
    surface = UsdShade.Shader.Define(stage, path + "/Surface")
    surface.CreateIdAttr("UsdPreviewSurface")
    surface.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    surface.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.85)
    surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)

    st_reader = UsdShade.Shader.Define(stage, path + "/stReader")
    st_reader.CreateIdAttr("UsdPrimvarReader_float2")
    st_reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    st_reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)

    tex = UsdShade.Shader.Define(stage, path + "/Texture")
    tex.CreateIdAttr("UsdUVTexture")
    tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(tex_rel)
    tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        st_reader.ConnectableAPI(), "result")
    tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)

    surface.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        tex.ConnectableAPI(), "rgb")
    mat.CreateSurfaceOutput().ConnectToSource(surface.ConnectableAPI(), "surface")
    return mat


def add_cylinder(stage, path, *, height, radius, y, material, axis="Y") -> None:
    cyl = UsdGeom.Cylinder.Define(stage, path)
    cyl.CreateAxisAttr(axis)
    cyl.CreateHeightAttr(height)
    cyl.CreateRadiusAttr(radius)
    # USD's bbox cache wants explicit extent for unbounded primitives.
    half = height / 2
    if axis == "Y":
        cyl.CreateExtentAttr([(-radius, -half, -radius), (radius, half, radius)])
        cyl.AddTranslateOp().Set(Gf.Vec3d(0, y, 0))
    elif axis == "X":
        cyl.CreateExtentAttr([(-half, -radius, -radius), (half, radius, radius)])
        cyl.AddTranslateOp().Set(Gf.Vec3d(0, y, 0))
    UsdShade.MaterialBindingAPI.Apply(cyl.GetPrim()).Bind(material)


def build_pylon(usda_path: Path, texture_rel: str) -> None:
    stage = Usd.Stage.CreateNew(str(usda_path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    root = UsdGeom.Xform.Define(stage, "/Pylon")
    stage.SetDefaultPrim(root.GetPrim())

    looks = UsdGeom.Scope.Define(stage, "/Pylon/Looks")
    ink = add_material(stage, "/Pylon/Looks/Ink", (0.05, 0.05, 0.05), roughness=0.6)
    paper = add_material(stage, "/Pylon/Looks/Paper", (0.97, 0.96, 0.90), roughness=0.8)
    hot = add_material(stage, "/Pylon/Looks/Hot", (1.0, 0.24, 0.18), roughness=0.55)
    banner_mat = add_textured_material(stage, "/Pylon/Looks/Banner", texture_rel)

    # Physically 5'6" so the presenter visibly clears the top of the pylon.
    # The banner above still says 5'7" — the audience reads the label, not a ruler.
    H = 1.6764  # 5'6" in meters
    base_h = 0.030
    post_r = 0.022

    # Base plate flush with the floor; engulfs the bottom of the post.
    add_cylinder(stage, "/Pylon/Base",
                 height=base_h, radius=0.18,
                 y=base_h / 2, material=ink)

    # Main post: from y=0 up to exactly 5'7".
    add_cylinder(stage, "/Pylon/Post",
                 height=H, radius=post_r,
                 y=H / 2, material=ink)

    # Foot tick rings at 1'–5'. 1 ft = 0.3048 m.
    for ft in range(1, 6):
        y = ft * 0.3048
        add_cylinder(stage, f"/Pylon/Tick_{ft}ft",
                     height=0.010, radius=0.075,
                     y=y, material=paper)

    # Hot-red "5'7" — YOU ARE MID" marker disk at the top of the post.
    add_cylinder(stage, "/Pylon/HereMarker",
                 height=0.028, radius=0.115,
                 y=H, material=hot)

    # Horizontal pointer arm jutting out the side at the 5'7" line.
    arm = UsdGeom.Cylinder.Define(stage, "/Pylon/Pointer")
    arm.CreateAxisAttr("X")
    arm.CreateHeightAttr(0.32)
    arm.CreateRadiusAttr(0.018)
    arm.CreateExtentAttr([(-0.16, -0.018, -0.018), (0.16, 0.018, 0.018)])
    arm.AddTranslateOp().Set(Gf.Vec3d(0.20, H, 0))
    UsdShade.MaterialBindingAPI.Apply(arm.GetPrim()).Bind(hot)

    # Arrowhead at the end of the pointer (a flat triangle plane).
    tip = UsdGeom.Mesh.Define(stage, "/Pylon/PointerTip")
    tip.CreatePointsAttr([(0, 0, 0), (-0.12, 0.07, 0), (-0.12, -0.07, 0)])
    tip.CreateFaceVertexCountsAttr([3])
    tip.CreateFaceVertexIndicesAttr([0, 1, 2])
    tip.CreateExtentAttr([(-0.12, -0.07, -0.002), (0, 0.07, 0.002)])
    tip.CreateDoubleSidedAttr(True)
    tip.AddTranslateOp().Set(Gf.Vec3d(0.42, H, 0))
    UsdShade.MaterialBindingAPI.Apply(tip.GetPrim()).Bind(hot)

    # Stem connecting the post top to the banner.
    stem_len = 0.16
    add_cylinder(stage, "/Pylon/BannerStem",
                 height=stem_len, radius=0.018,
                 y=H + 0.014 + stem_len / 2, material=ink)

    # Banner: flat double-sided rectangle with the MID texture.
    banner_w, banner_h = 0.62, 0.32
    banner_y = H + 0.014 + stem_len + banner_h / 2
    hw, hh = banner_w / 2, banner_h / 2

    banner = UsdGeom.Mesh.Define(stage, "/Pylon/Banner")
    banner.CreatePointsAttr([(-hw, -hh, 0), (hw, -hh, 0), (hw, hh, 0), (-hw, hh, 0)])
    banner.CreateFaceVertexCountsAttr([4])
    banner.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    banner.CreateExtentAttr([(-hw, -hh, -0.001), (hw, hh, 0.001)])
    banner.CreateDoubleSidedAttr(True)
    banner.AddTranslateOp().Set(Gf.Vec3d(0, banner_y, 0))

    uv_primvar = UsdGeom.PrimvarsAPI(banner).CreatePrimvar(
        "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
    uv_primvar.Set([(0, 0), (1, 0), (1, 1), (0, 1)])

    UsdShade.MaterialBindingAPI.Apply(banner.GetPrim()).Bind(banner_mat)

    stage.GetRootLayer().Save()


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    public = repo / "public"
    public.mkdir(exist_ok=True)
    work = Path(__file__).parent

    tex_path = work / "mid-banner.png"
    make_banner_texture(tex_path)
    print(f"wrote {tex_path} ({tex_path.stat().st_size} bytes)")

    usda_path = work / "pylon.usda"
    if usda_path.exists():
        usda_path.unlink()
    build_pylon(usda_path, "./mid-banner.png")
    print(f"wrote {usda_path}")

    usdz_path = public / "pylon.usdz"
    if usdz_path.exists():
        usdz_path.unlink()
    ok = UsdUtils.CreateNewUsdzPackage(str(usda_path), str(usdz_path))
    if not ok:
        raise RuntimeError("UsdUtils.CreateNewUsdzPackage failed")
    print(f"wrote {usdz_path} ({usdz_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
