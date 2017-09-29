# !/usr/bin/python
# -*- coding: utf-8 -*-

import hashlib
import time
import os

def generateMD5(code):
    now = time.time()
    m = hashlib.md5()
    m.update(str(now) + code)
    return m.hexdigest() # 生成唯一的MD5码


# 返回值为文件名,文件的相对路径(None表示处理过程出错了)
def createTmpFile(code):
    try:
        md5_string = generateMD5(code)
        filePath = "files/" + md5_string
        outFile = open(filePath,"w")
        outFile.write(code)
        outFile.close()
        return md5_string,filePath
    except Exception,e:
        print e
        return None,None

def createSha(code):
    try:
        md5_string = generateMD5(code)
        return md5_string
    except Exception,e:
        print e
        return None


# 调用sonar进行代码分析(返回0表示执行成功)
def analyze(tableName,id,language,fileName,filePath):
    # use the sonar to measure one version of the project
    rootdir = os.getcwd()
    absolutePath = os.path.join(rootdir, filePath)
    print absolutePath
    sonar_cmd = 'sonar-scanner -Dsonar.projectKey=' + tableName + ":" + str(id) + ' -Dsonar.projectName=' + tableName + ":" + str(id) \
                + ' -Dsonar.projectVersion=1.0 -Dsonar.sources=' + absolutePath + \
                ' -Dsonar.sourceEncoding=UTF-8'

    # 需要判断是不是执行成功了
    result = os.system(sonar_cmd)
    return result


# 将文件组合成工程项目
def assemble(sha,files):
    for f in files:
        relPath = sha + f["relPath"]
        path = sha + f["path"]
        code = f["code"]
        if os.path.exists(relPath) == False:
            os.makedirs(relPath)
        outFile = open(path,"w")
        outFile.write(code)
        outFile.close()
    rootdir = os.getcwd()
    absolutePath = os.path.join(rootdir, sha)
    return absolutePath # 返回最外层父节点的文件夹名字