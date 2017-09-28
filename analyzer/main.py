# !/usr/bin/python
# -*- coding: utf-8 -*-
import time
import MySQLdb
import utils
import os

conn_code = MySQLdb.connect(host="localhost",user="root",passwd="111111",db="CodePedia_test")
cursor_code = conn_code.cursor()

conn_sonar = MySQLdb.connect(host="localhost",user="root",passwd="111111",db="sonar")
cursor_sonar = conn_sonar.cursor()

# 定义一些常量
blob_table = "blobs"
function_table = "functions"

def findPointer(table_name):
    # 读取pointers表中的数据
    start_pointer = 1
    current_pointer = start_pointer
    end_pointer = start_pointer

    cursor_sonar.execute("select id,table_name,start_pointer,end_pointer,pointer from pointers where table_name=%s",(table_name,))
    pointerItem = cursor_sonar.fetchone()
    if pointerItem == None:
        # 表示还没有这条记录
        sql = "select min(id) as min_id, max(id) as max_id from " + table_name
        cursor_code.execute(sql)
        tmp = cursor_code.fetchone()
        min_id = tmp[0]
        max_id = tmp[1]
        cursor_sonar.execute("insert into pointers (table_name,start_pointer,end_pointer,pointer) values (%s,%s,%s,%s)",(table_name,min_id,max_id,min_id))
        conn_sonar.commit()
        print "插入了%s在pointers表中的记录" % (blob_table)
        start_pointer = min_id
        current_pointer = min_id
        end_pointer = max_id
    else:
        start_pointer = pointerItem[2]
        end_pointer = pointerItem[3]
        current_pointer = pointerItem[4]

    return start_pointer, current_pointer, end_pointer


if __name__ == "__main__":

    while True:
        # 处理blobs表
        blob_start_pointer, blob_current_pointer, blob_end_pointer = findPointer(blob_table)
        function_start_pointer, function_current_pointer, function_end_pointer = findPointer(function_table)

        # 获取未处理的数据
        cursor_code.execute("select id,path,code,project_id,file_index,language_id from blobs where id>=%s and id<=%s",(blob_current_pointer,blob_end_pointer))
        unhandleBlobs = cursor_code.fetchall()

        cursor_code.execute("select id,path,code,blob_id,project_id,function_index,language_id from functions where id>=%s and id<=%s",(function_current_pointer,function_end_pointer))
        unhandleFunctions = cursor_code.fetchall()

        # 读取所有的language
        languageMap = {}
        cursor_code.execute("select id,name from languages")
        languages = cursor_code.fetchall()
        for tmp in languages:
            id = tmp[0]
            language = tmp[1]
            languageMap[id] = language


        # 处理blobs表
        for unhandleBlob in unhandleBlobs:
            blob_id = unhandleBlob[0]
            print "handle %s:%s" % (blob_table,blob_id)
            blob_path = unhandleBlob[1]
            blob_code = unhandleBlob[2]
            blob_project_id = unhandleBlob[3]
            blob_file_index = unhandleBlob[4]
            blob_language_id = unhandleBlob[5]

            if languageMap.has_key(blob_language_id) == False:
                # 表示数据有问题
                continue
            blob_language = languageMap.get(blob_language_id)

            # 将代码封装成一个文件
            tmpFile,tmpFilePath = utils.createTmpFile(blob_code)

            if tmpFile == None:
                # 表示创建文件程序出问题了
                continue

            # 调用sonar进行代码分析
            utils.analyze(blob_table, blob_id, blob_language, tmpFile, tmpFilePath)
            # 删除文件
            os.remove(tmpFilePath)

            cursor_sonar.execute("update pointers set pointer=%s where table_name=%s",(blob_id + 1, blob_table))
            conn_sonar.commit()

        # 处理functions表
        for unhandleFunction in unhandleFunctions:
            function_id = unhandleFunction[0]
            print "handle %s:%s" % (function_table,function_id)
            function_path = unhandleFunction[1]
            function_code = unhandleFunction[2]
            function_blob_id = unhandleFunction[3]
            function_project_id = unhandleFunction[4]
            function_index = unhandleFunction[4]
            function_language_id = unhandleFunction[5]

            if languageMap.has_key(function_language_id) == False:
                # 表示数据有问题
                continue
            function_language = languageMap.get(function_language_id)

            # 将代码封装成一个文件
            tmpFile,tmpFilePath = utils.createTmpFile(function_code)

            if tmpFile == None:
                # 表示创建文件程序出问题了
                continue

            # 调用sonar进行代码分析
            utils.analyze(function_table, function_id, function_language, tmpFile, tmpFilePath)
            # 删除文件
            os.remove(tmpFilePath)

            cursor_sonar.execute("update pointers set pointer=%s where table_name=%s",(function_id + 1, function_table))
            conn_sonar.commit()

        # 查看end_pointer有没有发生变化
        sql = "select max(id) as max_id from " + blob_table
        cursor_code.execute(sql)
        tmp = cursor_code.fetchone()
        blob_end_pointer_new = tmp[0]

        sql = "select max(id) as max_id from " + function_table
        cursor_code.execute(sql)
        tmp = cursor_code.fetchone()
        function_end_pointer_new = tmp[0]

        if blob_end_pointer < blob_end_pointer_new:
            # 更新数据库
            cursor_sonar.execute("update pointers set end_pointer=%s where table_name=%s",(blob_end_pointer_new, blob_table))
            conn_sonar.commit()

        if function_end_pointer < function_end_pointer_new:
            # 更新数据库
            cursor_sonar.execute("update pointers set end_pointer=%s where table_name=%s",(function_end_pointer_new, function_table))
            conn_sonar.commit()

        if blob_end_pointer >= blob_end_pointer_new and function_end_pointer >= function_end_pointer_new:
            # 处理完了数据库中没有处理的数据
            print "开始休眠..."
            time.sleep(1800) # 单位是秒 (半个小时)