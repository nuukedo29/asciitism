import PIL
import PIL.Image
import PIL.ImageOps
import re
import exrex
import sys

width, height = 88, 88

COLORS = [
	# r" ",
	# r"\.",
	# r"[\'\`]",
	# r"\"",
	# r"\:",
	# r";",
	# r"\!",
	# r"\|",
	# r"[\?]",
	# r"[\-\+\_]",
	# r"[a-z0-9]",
	# r"[A-Z]",
	# r"#",
	# r"\@"
	r" ",
	r"[\.\,]",
	r"[\'\"]",
	r"\:\;",
	r"[a-z0-9]",
	r"[A-Z]",
	r"[\@\#]"
]

code = open("Ch4Practice.java", "rb").read()

image = PIL.Image.open("Untitled.png")
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

def tokenize_java(code):

	def lookup_strings(code):
		positions = []
		for match in re.finditer(rb"('[^']*'|\"[^\"]*\")", code):
			positions.append([match.span()[0], match.span()[1]])
		return positions

	def lookup_comments(code):
		positions = []
		for match in re.finditer(rb"(?sm)(\/\*.*?\*\/)", code):
			positions.append([match.span()[0], match.span()[1]])
		return positions

	def is_position_illegal(start_pos, end_pos, positions):
		for [_start_pos, _end_pos] in positions:
			if set(range(_start_pos, _end_pos)).intersection(range(start_pos, end_pos)):
				return True
		return False

	def subn_but_careful(pattern, replacement, string):
		replacement_offset = 0
		for match in re.finditer(pattern, string):
			positions = [*lookup_strings(string), *lookup_comments(string)]
			if not is_position_illegal(match.span()[0]+replacement_offset, match.span()[1]+replacement_offset, positions):
				replacement_token = replacement.replace(b"\g<1>", (match.groups() or [b""])[0])
				string = string[:match.span()[0]+replacement_offset] + replacement_token + string[match.span()[1]+replacement_offset:]
				replacement_offset += len(replacement_token) - (match.span()[1] - match.span()[0])
		return string

	def tokenize_strings(string):
		replacement_offset = 0
		for match in re.finditer(rb"('[^']*'|\"[^\"]*\")", string):
			replacement_token = b"+".join([bytes([match.groups()[0][0]]) + bytes([char]) + bytes([match.groups()[0][0]]) for char in match.groups()[0][1:-1]]) 
			string = string[:match.span()[0]+replacement_offset] + replacement_token + string[match.span()[1]+replacement_offset:]
			replacement_offset += len(replacement_token) - (match.span()[1] - match.span()[0])
		return string

	code = tokenize_strings(code)
	code = subn_but_careful(rb"(?m)//(.*?)$", b"/*\g<1>*/", code)
	code = subn_but_careful(rb"(\|\||\+\+|\-\-|\=\=\=|\=\=|[\!\*\+\-\/\<\>]\=|[\*\+\-\/\=]|[\{\}\[\]\;\(\)\<\>\%\!\,\?\:])", b" \g<1> ", code)
	code = subn_but_careful(rb"('.*?'|\".*?\")", b" \g<1> ", code)
	code = subn_but_careful(rb"\s+", b" ", code)
	return re.findall(rb"[^\s]+", code)

output = open("output.txt", "wb")

tokens = tokenize_java(code)
token_offset = 0

def pixel_lookahead(image, x, y, distance):
	buffer = []
	for n in range(0,distance):
		buffer.append(image.getpixel((x+n, y)))
	return buffer

def color_distance(buffer1, buffer2):
	total = 0
	for n in range(0,len(buffer1)):
		total += abs(buffer1[n] - buffer2[n])
	return total

image.save("gay.png")

for y in range(0, height-1):
	skip_rows = 0
	for x in range(0, width-1):
		if skip_rows:
			skip_rows -= 1
			continue

		token = None if token_offset+1 > len(tokens) else tokens[token_offset]
		token_size = len(token) if token else 0

		distance_left = width - 1 - x 

		if tokens and token_size >= width-1: # if its bigger - then fuck it
			output.write(token + b" ")
			token_offset += 1
			skip_rows += token_size + 1

		elif tokens and distance_left >= token_size and color_distance(pixel_lookahead(image, x, y, token_size), token) < token_size*150: # if code looks kinda like the image
			output.write(token + b" ")
			token_offset += 1
			skip_rows += token_size + 1

		# elif distance_left > 20:
		# 	output.write(b"/*")
		# 	for pixel in pixel_lookahead(image, x, y, distance_left)[2:-2]:
		# 		output.write(exrex.getone(color_to_pattern(pixel)).encode("utf8"))
		# 	output.write(b"*/")
		# 	skip_rows += distance_left
			
		else:
			output.write(b" ")
			# skip_rows += distance_left

	output.write(b"\n")

output.write(b" ".join(tokens[token_offset:]))