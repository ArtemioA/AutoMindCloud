import os
from IPython.display import Image, display

image_name = "AutoMindCloud.png"
image_path = None

for root, dirs, files in os.walk('.'):
    if image_name in files:
        image_path = os.path.join(root, image_name)
        break

if image_path:
    display(Image(filename=image_path))
