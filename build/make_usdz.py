#!/usr/bin/env python3
"""
Generate a minimalist XKCD-style stick figure as a USDZ file.

Geometry: head sphere + body/arms/legs as thin cylinders.
All black UsdPreviewSurface, feet at y=0 so it lands on AR floor plane.

Default height: 1.65 m (global average human height).
"""

import math
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def build_usda(height: float = 1.65) -> str:
    H = height

    # Proportions tuned for an XKCD look at 1.65m.
    stick_r = 0.028
    head_r = 0.13

    head_cy = H - head_r
    body_top = head_cy - head_r
    crotch_y = 0.85 * (H / 1.65)
    body_len = body_top - crotch_y
    body_cy = (body_top + crotch_y) / 2

    # Arms: anchored just below the top of the body, swinging out at 30 deg from vertical.
    arm_anchor_y = body_top - 0.04
    arm_len = 0.50 * (H / 1.65)
    arm_angle_deg = 30.0
    arm_angle = math.radians(arm_angle_deg)
    arm_dx = arm_len * math.sin(arm_angle)
    arm_dy = -arm_len * math.cos(arm_angle)

    arm_mid_x = arm_dx / 2
    arm_mid_y = arm_anchor_y + arm_dy / 2

    # rotateZ to take Y-axis cylinder onto the arm direction.
    # left arm direction = (-sin a, -cos a). Solve (-sin θ, cos θ) = (-sin a, -cos a)
    # => sin θ = sin a, cos θ = -cos a => θ = 180° - a
    left_arm_rot = 180.0 - arm_angle_deg
    right_arm_rot = -(180.0 - arm_angle_deg)

    # Legs: from crotch out to feet at y=0, stance ~24cm wide.
    foot_x = 0.12
    leg_dx = -foot_x
    leg_dy = -crotch_y
    leg_len = math.hypot(leg_dx, leg_dy)
    leg_mid_x = leg_dx / 2
    leg_mid_y = crotch_y + leg_dy / 2

    leg_dir_x = leg_dx / leg_len
    leg_dir_y = leg_dy / leg_len
    # (-sin θ, cos θ) = (leg_dir_x, leg_dir_y) => sin θ = -leg_dir_x, cos θ = leg_dir_y
    left_leg_rot = math.degrees(math.atan2(-leg_dir_x, leg_dir_y))
    right_leg_rot = -left_leg_rot

    # Common metadata block for any prim that binds a material
    api = '(\n            prepend apiSchemas = ["MaterialBindingAPI"]\n        )'

    return dedent(f"""\
        #usda 1.0
        (
            defaultPrim = "StickFigure"
            metersPerUnit = 1
            upAxis = "Y"
        )

        def Xform "StickFigure"
        {{
            double3 xformOp:translate = (0, {stick_r}, 0)
            uniform token[] xformOpOrder = ["xformOp:translate"]

            def Sphere "head" {api}
            {{
                double radius = {head_r}
                rel material:binding = </StickFigure/Looks/Black>
                double3 xformOp:translate = (0, {head_cy}, 0)
                uniform token[] xformOpOrder = ["xformOp:translate"]
            }}

            def Cylinder "body" {api}
            {{
                uniform token axis = "Y"
                double height = {body_len}
                double radius = {stick_r}
                rel material:binding = </StickFigure/Looks/Black>
                double3 xformOp:translate = (0, {body_cy}, 0)
                uniform token[] xformOpOrder = ["xformOp:translate"]
            }}

            def Cylinder "leftArm" {api}
            {{
                uniform token axis = "Y"
                double height = {arm_len}
                double radius = {stick_r}
                rel material:binding = </StickFigure/Looks/Black>
                double xformOp:rotateZ = {left_arm_rot}
                double3 xformOp:translate = ({-arm_mid_x}, {arm_mid_y}, 0)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateZ"]
            }}

            def Cylinder "rightArm" {api}
            {{
                uniform token axis = "Y"
                double height = {arm_len}
                double radius = {stick_r}
                rel material:binding = </StickFigure/Looks/Black>
                double xformOp:rotateZ = {right_arm_rot}
                double3 xformOp:translate = ({arm_mid_x}, {arm_mid_y}, 0)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateZ"]
            }}

            def Cylinder "leftLeg" {api}
            {{
                uniform token axis = "Y"
                double height = {leg_len}
                double radius = {stick_r}
                rel material:binding = </StickFigure/Looks/Black>
                double xformOp:rotateZ = {left_leg_rot}
                double3 xformOp:translate = ({leg_mid_x}, {leg_mid_y}, 0)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateZ"]
            }}

            def Cylinder "rightLeg" {api}
            {{
                uniform token axis = "Y"
                double height = {leg_len}
                double radius = {stick_r}
                rel material:binding = </StickFigure/Looks/Black>
                double xformOp:rotateZ = {right_leg_rot}
                double3 xformOp:translate = ({-leg_mid_x}, {leg_mid_y}, 0)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateZ"]
            }}

            def Scope "Looks"
            {{
                def Material "Black"
                {{
                    token outputs:surface.connect = </StickFigure/Looks/Black/Surface.outputs:surface>

                    def Shader "Surface"
                    {{
                        uniform token info:id = "UsdPreviewSurface"
                        color3f inputs:diffuseColor = (0, 0, 0)
                        float inputs:metallic = 0
                        float inputs:roughness = 0.85
                        float inputs:opacity = 1
                        token outputs:surface
                    }}
                }}
            }}
        }}
        """)


def main():
    out_dir = Path(__file__).resolve().parent.parent
    public = out_dir / "public"
    public.mkdir(exist_ok=True)

    usda_path = Path(__file__).parent / "figure.usda"
    usdz_path = public / "figure.usdz"

    height_m = 1.65
    usda_path.write_text(build_usda(height_m))
    print(f"wrote {usda_path} (height: {height_m} m / {height_m * 39.37:.1f} in)")

    # Validate USDA before packaging (usdcat round-trips through .usda).
    subprocess.run(
        ["usdcat", str(usda_path), "--out", str(usda_path.with_suffix(".roundtrip.usda"))],
        check=True,
    )
    usda_path.with_suffix(".roundtrip.usda").unlink()

    # Package with usdzip (handles 64-byte file alignment per USDZ spec).
    # Run from the USDA's directory so the archive uses a bare filename, not absolute path.
    if usdz_path.exists():
        usdz_path.unlink()
    subprocess.run(
        ["usdzip", str(usdz_path), usda_path.name],
        check=True,
        cwd=usda_path.parent,
    )

    size = usdz_path.stat().st_size
    print(f"wrote {usdz_path} ({size} bytes)")


if __name__ == "__main__":
    sys.exit(main())
