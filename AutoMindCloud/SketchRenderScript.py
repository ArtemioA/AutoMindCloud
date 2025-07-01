import cadquery as cq
from cadquery import exporters
from IPython.display import display, SVG

# Load the STEP file
#result = cq.importers.importStep('Sketch.step')
# Function to rotate and display the object

def show_view(result,rotate_axis, rotate_angle, title=""):
    # Rotate the object
    rotated = result.rotate((0,0,0), rotate_axis, rotate_angle)
    # Export as SVG
    svg_str = exporters.getSVG(rotated.val())
    display(SVG(svg_str))
    print(title)

def SketchRender(Sketch_Name):
  result = cq.importers.importStep(Sketch_Name)
  # Standard views using rotation
  show_view(result,(1,0,0), 0, "Front View")
  show_view(result,(1,0,0), 90, "Top View")
  show_view(result,(0,1,0), 90, "Right Side View")

  # Isometric view (rotate 45° around X then 30° around Z)
  #rotated = result.rotate((0,0,0), (1,0,0), 45).rotate((0,0,0), (0,0,1), 30)
  #svg_str = exporters.getSVG(rotated.val())
  #display(SVG(svg_str))
  #print("Isometric View")
