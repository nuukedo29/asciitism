import PIL
import PIL.Image
import PIL.ImageOps
import re
import exrex
import sys

COLORS = [
	r" ",
	r"\.",
	r"\'",
	r"\:",
	r"[a-z]",
	r"[0-9]",
	r"\@",
	r"\#",
	r"\|",
	r"\!"
]

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
			replacement_token = b"+".join([bytes([match.groups()[0][0]]) + char.encode("utf8") + bytes([match.groups()[0][0]]) for char in re.findall(r"(\\.|.)", match.groups()[0][1:-1].decode("utf8"))] or [b"\"\""]) 
			string = string[:match.span()[0]+replacement_offset] + replacement_token + string[match.span()[1]+replacement_offset:]
			replacement_offset += len(replacement_token) - (match.span()[1] - match.span()[0])
		return string

	code = tokenize_strings(code)
	code = subn_but_careful(rb"(?m)//(.*?)$", b"/*\g<1>*/", code)
	code = subn_but_careful(rb"(\|\||\+\+|\-\-|\=\=\=|\=\=|[\!\*\+\-\/\<\>]\=|[\*\+\-\/\=]|[\{\}\[\]\;\(\)\<\>\%\!\,\?\:])", b" \g<1> ", code)
	code = subn_but_careful(rb"('.*?'|\".*?\")", b" \g<1> ", code)
	code = subn_but_careful(rb"\s+", b" ", code)
	return re.findall(rb"[^\s]+", code)

def pixel_lookahead(image, x, y, distance):
	buffer = []
	for n in range(0, distance):
		buffer.append(image.getpixel((x+n, y)))
	return buffer

def can_emit(buffer, length, max):
	if [len(item[0]) for item in re.findall(r"((.)\2*)", "".join(map(str, buffer)))] == length:
		pos = "".join(map(str, buffer)).find(item[0])
		if pos + length < max - 4:
			return True, pos
	return False, 0

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print(f"Usage: {sys.argv[0]} <source code> <image> <output>\n")
		sys.exit(1)
	input = open(sys.argv[1], "rb").read()
	tokens = tokenize_java(input)
	image = PIL.Image.open(sys.argv[2])
	image.load()
	image = image.resize((int(image.size[0] / 8), int(image.size[1] / 16)), PIL.Image.LANCZOS) # for some *cursed* reason thumbnail feels the compulsive urge to maintain aspect ratio
	image = PIL.ImageOps.grayscale(image)
	image = image.quantize(len(COLORS))

	width, height = image.size

	print(f"Output will be {width}x{height}")

	output = open(sys.argv[3], "wb")
	token_offset = 0

	for y in range(0, height):
		distance_left = width
		for x in range(0, width):
			# ask nicely for a token
			token = None if token_offset + 1 > len(tokens) else tokens[token_offset]
			token_size = len(token.decode("utf8")) if token else 0

			#print(y, token, token_size, distance_left)

			if token and distance_left > token_size and len(set(pixel_lookahead(image, x, y, token_size))) == 1:
				# if the string here is the same character repeated and it is the size of our token emit
				output.write(token)
				token_offset += 1
				distance_left -= token_size
			elif token and distance_left > token_size and can_emit(pixel_lookahead(image, x, y, distance_left), token_size, distance_left):
				# if we find a needle, search for pos and write padding until we can write the requested token
				# this is awful
				_, pos = can_emit(pixel_lookahead(image, x, y, distance_left), token_size, distance_left)
				output.write(b"/*")
				distance_left -= 2
				for n in range(0, pos):
					output.write(exrex.getone(color_to_pattern(pixel_lookahead(image, x, y, distance_left)[1:-1][n])).encode("utf8"))
				output.write(b"*/")
				distance_left -= 2
				output.write(token)
				token_offset += 1
				distance_left -= token_size
			elif distance_left >= 4:
				# add a comment block
				output.write(b"/*")
				distance_left -= 2
				for pixel in pixel_lookahead(image, x, y, distance_left)[1:-1]:
					output.write(exrex.getone(color_to_pattern(pixel)).encode("utf8"))
					distance_left -= 1
				output.write(b"*/")
				distance_left -= 2
				break
			elif distance_left >= 2:
				output.write(b"//" + b"/" if distance_left == 3 else b"")
				distance_left -= distance_left
				break
			else:
				# quite the travesty, we cannot do anything here
				#print("Can't emit comment. tears in rain... Time to die") # <3 keybagd
				break
		output.write(b"\n")

	if tokens[token_offset:]:
		output.write(b"/* extra tokens */\n" + b" ".join(tokens[token_offset:]))