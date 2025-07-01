from IPython.display import display, Image
import os

def show_image():
    # Get the directory where __init__.py is located
    dir_path = os.path.dirname(os.path.realpath(__file__))
    image_path = os.path.join(dir_path, 'AutoMindCloud.png')
    
    # Check if the image exists
    if os.path.exists(image_path):
        display(Image(filename=image_path))
    else:
        print(f"Image not found at: {image_path}")

# Optionally, automatically display the image when the module is imported
show_image()
