"""
Generate all required icon sizes for Tauri from source PNG
"""
import sys
import io

# Set UTF-8 encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from PIL import Image
import os

source_icon = "images/Whisper4Windows-icon.png"
output_dir = "frontend/src-tauri/icons"

# Icon sizes required by Tauri
icon_sizes = {
    "icon.png": 1024,
    "32x32.png": 32,
    "128x128.png": 128,
    "128x128@2x.png": 256,
    "Square30x30Logo.png": 30,
    "Square44x44Logo.png": 44,
    "Square71x71Logo.png": 71,
    "Square89x89Logo.png": 89,
    "Square107x107Logo.png": 107,
    "Square142x142Logo.png": 142,
    "Square150x150Logo.png": 150,
    "Square284x284Logo.png": 284,
    "Square310x310Logo.png": 310,
    "StoreLogo.png": 50,
}

print(f"📦 Loading source icon: {source_icon}")
img = Image.open(source_icon)
print(f"   Source size: {img.size}")

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Generate PNG files
print("\n🎨 Generating PNG icons...")
for filename, size in icon_sizes.items():
    output_path = os.path.join(output_dir, filename)
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    resized.save(output_path, "PNG")
    print(f"   ✅ {filename} ({size}x{size})")

# Generate .ico file (Windows)
print("\n🪟 Generating Windows .ico file...")
ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
ico_images = [img.resize(size, Image.Resampling.LANCZOS) for size in ico_sizes]
ico_path = os.path.join(output_dir, "icon.ico")
ico_images[0].save(
    ico_path,
    format='ICO',
    sizes=ico_sizes,
    append_images=ico_images[1:]
)
print(f"   ✅ icon.ico (multi-size: 16, 32, 48, 64, 128, 256)")

# Generate .icns file (macOS)
print("\n🍎 Generating macOS .icns file...")
try:
    from PIL import Image
    import subprocess

    # Create temporary iconset directory
    iconset_dir = "temp_iconset.iconset"
    os.makedirs(iconset_dir, exist_ok=True)

    # macOS icon sizes
    icns_sizes = [
        (16, "16x16"),
        (32, "16x16@2x"),
        (32, "32x32"),
        (64, "32x32@2x"),
        (128, "128x128"),
        (256, "128x128@2x"),
        (256, "256x256"),
        (512, "256x256@2x"),
        (512, "512x512"),
        (1024, "512x512@2x"),
    ]

    for size, name in icns_sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(os.path.join(iconset_dir, f"icon_{name}.png"), "PNG")

    # Try to use iconutil (macOS only)
    icns_path = os.path.join(output_dir, "icon.icns")
    try:
        subprocess.run(
            ["iconutil", "-c", "icns", iconset_dir, "-o", icns_path],
            check=True
        )
        print(f"   ✅ icon.icns (macOS)")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"   ⚠️  iconutil not available (macOS only), skipping .icns generation")
        print(f"      Existing .icns will be kept")

    # Clean up temporary directory
    import shutil
    shutil.rmtree(iconset_dir, ignore_errors=True)

except Exception as e:
    print(f"   ⚠️  Could not generate .icns: {e}")
    print(f"      Existing .icns will be kept")

print("\n✅ Icon generation complete!")
print(f"   Output directory: {output_dir}")
