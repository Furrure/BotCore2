import os
import shutil
localprint = print

def print(*args, end="\n"):
	final = ""
	for param in args:
		final += " " + str(param)
		
	localprint(final + str(end))

def input(string):
	return input(string)
	
def write_file(file_path, contents):
	with open(file_path, "wb") as file:
		file.write(contents)

def read_file(file_path):
	content = None
	with open(file_path, "rb") as file:
		content = file.read()
	return content

def append_to_file(file_path, content):
	with open(file_path, "ab") as file:
		file.write(content.encode())
	
def openfile(*args, **kwargs):
	return open(*args, **kwargs)

def mkdir(file_path):
	os.mkdir(file_path)

def rmtree(file_path):
	shutil.rmtree(file_path)

def isfile(file_path):
	return os.path.isfile(file_path)

def isdir(file_path):
	return os.path.isdir(file_path)

def listdir(file_path):
	return os.listdir(file_path)

def config_read(file_path, value_if_non_existant):
	if not(isfile(file_path)):
		opened = openfile(file_path, "wb")
		opened.write(value_if_non_existant.encode("utf-8"))
		opened.close()
		opened = openfile(file_path, "rb")
		content = opened.read()
		opened.close()
		return content.decode("utf-8")
	else:
		return read_file(file_path).decode()

def get_working_directory():
	return os.getcwd()
	