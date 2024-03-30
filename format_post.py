import os
import time
import re

def main():
    prefix = time.strftime("%Y-%m-%d-", time.localtime(time.time()))
    for parent, dirnames, filenames in os.walk('./_posts'):
        for filename in filenames:
            # print("parent is: " + parent)
            # print("filename is: " + filename)
            #1、重命名文件
            if filename.startswith('20'):
                print(filename, os.path.join(parent, filename))
            else:
                oldname=filename
                filename=prefix+oldname
                print(filename, os.path.join(parent, filename))
                os.rename(os.path.join(parent, oldname), os.path.join(parent, filename))

            filepath = os.path.join(parent, filename)
            #2、如果没有模板文章头部，则插入
            title = filename[11:]
            if not title.endswith('.md'):
                print("abnormal file: ", filepath)
                continue
            title = title[:-3]
            dirnames = parent.split('/')
            if len(dirnames) < 3:
                print("abnormal parent:", parent)
                continue
            category = dirnames[2]
            rooturl = os.path.relpath('.', parent)
            print(title, category, rooturl)

            with open(filepath, 'r+') as f:
                content = f.read()
                if re.search(r'^\s*---', content) == None:
                    f.seek(0)
                    f.write("---\nlayout: post\ntitle: %s\ncategory: %s\ntypora-root-url: %s\n---\n\n" % (title, category, rooturl))
                    f.write(content)

def list_files(dir):
    for root, dirs, files in os.walk(dir):
        for file in files:
            file_path = os.path.join(root, file)
            print(file_path)
            modify_file(file_path)
def read_file(file):
    with open(file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            print(line.strip())
def modify_file(file):
    with open(file, 'r+') as f:
        content = f.read()
        modified_content = content.upper()
        f.seek(0)
        f.write(modified_content)
        f.truncate()


main()
