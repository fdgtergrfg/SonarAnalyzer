# !/usr/bin/python
# -*- coding: utf-8 -*-

import hashlib
import time
import os
import subprocess

def generateMD5(code):
    now = time.time()
    m = hashlib.md5()
    m.update(str(now) + code)
    return m.hexdigest() # 生成唯一的MD5码


# 返回值为文件名,文件的相对路径(None表示处理过程出错了)
def createTmpFile(code):
    try:
        md5_string = generateMD5(code)
        filePath = "../files/" + md5_string
        outFile = open(filePath,"w")
        outFile.write(code)
        outFile.close()
        return md5_string,filePath
    except Exception,e:
        print e
        return None,None


# 调用sonar进行代码分析
def analyze(tableName,id,language,fileName,filePath):
    # use the sonar to measure one version of the project
    sonar_cmd = 'sonar-scanner -Dsonar.projectKey=' + tableName + ":" + str(id) + ' -Dsonar.projectName=' + fileName \
                + ' -Dsonar.projectVersion=1.0 -Dsonar.sources=' + filePath + \
                ' -Dsonar.sourceEncoding=UTF-8 -Dsonar.language=' + str(language).lower()



    # cmd_git_log = ["sonar-scanner",
    #                "-Dsonar.projectKey=" + tableName + ":" + str(id),
    #                "-Dsonar.projectName=" + fileName,
    #                "-Dsonar.projectVersion=1.0",
    #                "-Dsonar.sources=" + filePath,
    #                "-Dsonar.sourceEncoding=UTF-8",
    #                "-Dsonar.language=" + str(language).lower()]
    #
    # proc = subprocess.Popen(cmd_git_log,
    #                 stdout=subprocess.PIPE,
    #                 stderr=subprocess.PIPE)

    # result, error = proc.communicate()
    # 需要判断是不是执行成功了
    result, error = os.popen([sonar_cmd])
    print "result"


# 搬运分析结果函数
def moveResult():

    print "move analyze result"