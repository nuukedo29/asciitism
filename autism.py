import PIL
import PIL.Image
import PIL.ImageOps
import re
import exrex
import sys

width, height = 88, 88

COLORS = [
	r" ",
	r"\.",
	r"[\'\`]",
	r"\"",
	r"\:",
	r";",
	r"\!",
	r"\|",
	r"[\?]",
	r"[\-\+\_]",
	r"[a-z0-9]",
	r"[A-Z]",
	r"#",
	r"\@"
]

code = open("code.txt", "r", encoding="utf8").read()

image = PIL.Image.open(sys.argv[1])
image.load()
image.thumbnail((width, height), PIL.Image.ANTIALIAS)
image = PIL.ImageOps.grayscale(image)
image = image.quantize(len(COLORS))

width, height = image.size

def ascii_to_color(char):
	for color, pattern in enumerate(COLORS):
		if re.match(pattern, char):
			return color
	return 2

def color_to_pattern(color):
	for _color, pattern in enumerate(COLORS):
		if _color == color:
			return pattern

output = open("output.txt", "w", encoding="utf8")
code_offset = 0

print(width, height)

for y in range(0, height-1, 2):
	for x in range(0, width-1):
		pixel = image.getpixel((x, y))
		# char = code[code_offset]
		# char_color = ascii_to_color(char)

		# print(color_to_pattern(pixel))

		output.write(exrex.getone(color_to_pattern(pixel)))
		# if pixel == char_color:
		# 	output.write(char)
		# 	code_offset += 1
		# else: 
		# 	output.write(" ")
			
	output.write("\n")