# Regenerates the app icons from icons/tailslab.png (1024x1024):
#   - icons/tailslab.ico          Windows executable + installer
#   - icons/tailslab.icns         macOS app bundle
#   - icons/tailslab-256.png      Linux desktop entry
#   - frontend/src/favicon.ico    GUI window / browser tab
#   - frontend/src/assets/logo.png  GUI toolbar and landing page
#
# Run `python icons/generate_icons.py` from the project root after replacing icons/tailslab.png. Needs Pillow.

from PIL import Image

SOURCE = 'icons/tailslab.png'
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

if __name__ == '__main__':
    image = Image.open(SOURCE).convert('RGBA')
    image.save('icons/tailslab.ico', sizes=ICO_SIZES)
    image.save('icons/tailslab.icns')
    image.resize((256, 256), Image.Resampling.LANCZOS).save('icons/tailslab-256.png', optimize=True)
    image.save('frontend/src/favicon.ico', sizes=ICO_SIZES[:5])
    image.resize((256, 256), Image.Resampling.LANCZOS).save('frontend/src/assets/logo.png', optimize=True)
