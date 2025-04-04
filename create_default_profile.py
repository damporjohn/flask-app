from PIL import Image, ImageDraw

# Create a new image with a white background
size = (200, 200)
img = Image.new('RGB', size, 'white')
draw = ImageDraw.Draw(img)

# Draw a light gray circle for the profile
circle_color = '#E0E0E0'
draw.ellipse([40, 40, 160, 160], fill=circle_color)

# Draw a lighter gray shape for the head
head_color = '#F5F5F5'
draw.ellipse([70, 60, 130, 120], fill=head_color)

# Draw the body shape
body_color = '#F5F5F5'
draw.ellipse([60, 110, 140, 180], fill=body_color)

# Save the image
img.save('static/images/default_profile.png') 