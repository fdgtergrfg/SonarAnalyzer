# !/usr/bin/python
# -*- coding: utf-8 -*-
import os
import time

import MySQLdb

import utils

conn_code = MySQLdb.connect(host="localhost",user="root",passwd="111111",db="code_pedia")
cursor_code = conn_code.cursor()
conn_code.autocommit(False)

conn_sonar = MySQLdb.connect(host="localhost",user="root",passwd="111111",db="sonar")
cursor_sonar = conn_sonar.cursor()

# 定义一些常量
sonar_table = "sonar_results"

def createTable(table_name):
    sql = "CREATE TABLE IF NOT EXISTS " + table_name + " (`id` int(11) NOT NULL AUTO_INCREMENT, " \
          "`project_id` int(11) DEFAULT NULL, " \
          "`blob_id` int(11) DEFAULT NULL, " \
          "`blob_line` int(11) DEFAULT NULL, " \
          "`function_id` int(11) DEFAULT NULL," \
          "`function_line` int(11) DEFAULT NULL," \
          "`rule_id` int(11) DEFAULT NULL, " \
          "`rule_name` varchar(255) DEFAULT NULL, " \
          "`rule_priority` int(11) DEFAULT NULL, " \
          "`message` varchar(4000) DEFAULT NULL, " \
          "`effort` int(11) DEFAULT NULL, " \
          "`status` varchar(20) DEFAULT NULL, " \
          "`severity` varchar(10) DEFAULT NULL, " \
	  "`has_question` int(2) DEFAULT 0, " \
          "PRIMARY KEY (`id`), " \
          "KEY `project_id` (`project_id`), " \
          "KEY `blob_id` (`blob_id`), " \
          "KEY `rule_id` (`rule_id`), " \
          "KEY `rule_name` (`rule_name`), " \
          "KEY `rule_priority` (`rule_priority`), " \
          "KEY `effort` (`effort`), " \
          "KEY `status` (`status`)," \
          "KEY `function_id` (`function_id`)" \
          ") ENGINE=InnoDB DEFAULT CHARSET=utf8;"
    cursor_code.execute(sql)
    conn_code.commit()


# 搬运分析结果函数
def moveResult(project_id,projectKey,projectName):
    createTable(sonar_table) # 如果结果表不存在则创建一个新的

    # 读取当前项目function_lineNum和blob_lineNum的对应关系
    lineNumMap = {}
    cursor_code.execute("select file_linenum,function_linenum,function_id,file_id from `projects_line` where project_id=%s",(project_id,))
    items = cursor_code.fetchall()
    for item in items:
        blob_linenum = item[0]
        function_linenum = item[1]
        function_id = item[2]
        blob_id = item[3]
        lineNumMap.setdefault(blob_id,{})
        lineNumMap[blob_id][blob_linenum] = {"function_id":function_id,"function_linenum":function_linenum}


    # 读取当前project_id对应blobs表中所有的文件
    cursor_code.execute("select id,path from projects_file where project_id=%s",(project_id,))
    blobs = cursor_code.fetchall()
    blobMap = {} # 用于存储当前项目的blob路径和id对应关系
    if len(blobs) == 0:
        # 表示没有对应project的blob文件
        print "没有找到对应project的blob文件"
        return None
    for blob in blobs:
        blob_id = blob[0]
        blob_path = blob[1]
        blobMap[blob_path] = blob_id

    # 读取所有的rules表中的数据
    ruleMap = {}
    try:
        cursor_sonar.execute("select id,name,plugin_rule_key,plugin_name,priority from rules")
        items = cursor_sonar.fetchall()
        for item in items:
            id = item[0]
            name = item[1]
            plugin_rule_key = item[2]
            plugin_name = item[3]
            priority = item[4]
            rule = {"name":name, "plugin_rule_key":plugin_rule_key, "plugin_name":plugin_name, "priority":priority}
            ruleMap[id] = rule
    except Exception,e:
        print "没有rule表"
        return None

    # 读取当前项目在projects表中的基本信息
    cursor_sonar.execute("select project_uuid from projects where kee=%s",(projectKey,))
    project = cursor_sonar.fetchone()
    if project == None:
        print "没有读取到当前项目在sonar数据库中的信息"
        return None
    project_uuid = project[0]
    print "project_uuid=%s" % (project_uuid)    

    # 读取project对应的所有文件级别的component_uuid
    cursor_sonar.execute("select uuid,path from projects where project_uuid=%s and scope=%s",(project_uuid,"FIL"))
    items_projects = cursor_sonar.fetchall()
    print "%s files in this project have issues" % (len(items))
    for item_project in items_projects:
        component_uuid = item_project[0]
        component_path = item_project[1]
        if component_path != None and str(component_path).find(projectName) >= 0:
            component_path = component_path[len(projectName):] # 获取文件的相对路径
        else:
            continue
        # 获取当前component对应的blob_id
        blob_id = None
        if blobMap.has_key(component_path) == False:
            continue
        else:
            blob_id = blobMap[component_path]

        # 读取issues表对应的数据
        cursor_sonar.execute("select id,kee,rule_id,severity,message,line,status,effort,created_at,updated_at,issue_creation_date,issue_update_date,tags,component_uuid,issue_type from issues where component_uuid=%s",(component_uuid,))
        items = cursor_sonar.fetchall()
        print "this file has %s issues" % (len(items))
        for item in items:
            id = item[0]
            kee = item[1]
            rule_id = item[2]
            severity = item[3]
            message = item[4]
            blob_line = item[5]
            status = item[6]
            effort = item[7]
            created_at = item[8]
            updated_at = item[9]
            issue_creation_date = item[10]
            issue_update_date = item[11]
            tags = item[12]
            component_uuid = item[13]
            issue_type = item[14]
            rule_name = None
            rule_priority = None
            function_id = None # 用于记录对应到哪个方法的哪一行
            function_linenum = None

            if ruleMap.has_key(rule_id) == True:
                rule_name = ruleMap[rule_id]["name"]
                rule_priority = ruleMap[rule_id]["priority"]
            else:
                # 表示数据有问题
                continue

            if lineNumMap.has_key(blob_id) == True and lineNumMap[blob_id].has_key(blob_line) == True:
                # 表示数据没有问题
                tmp = lineNumMap[blob_id][blob_line]
                function_id = tmp["function_id"]
                function_linenum = tmp["function_linenum"]

            # 将结果存储到数据库中
            cursor_code.execute("insert into sonar_results (project_id,blob_id,blob_line,function_id,function_line,rule_id,rule_name,rule_priority,message,effort,status,severity) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                (project_id,blob_id,blob_line,function_id,function_linenum,rule_id,rule_name,rule_priority,message,effort,status,severity))
    conn_code.commit()

    print "完成了项目:%s分析结果数据的迁移" % (project_id)


if __name__ == "__main__":

    createTable(sonar_table)

    while True:

        # 判断哪些projects已经被处理过了
        handledProjects = set()
        try:
            cursor_sonar.execute("select kee,project_uuid from projects where scope=%s",("PRJ",))
            tmps = cursor_sonar.fetchall()
            for tmp in tmps:
                kee = tmp[0]
                project_uuid = tmp[1]
                # 查看issues表中有没有对应的issue
                cursor_sonar.execute("select * from issues where project_uuid=%s",(project_uuid,))
                issueList = cursor_sonar.fetchall()
                if len(issueList) <= 0:
                    # 表示处理的过程中出错了
                    continue
                else:
                    # 表示确实处理过了
                    handledProjects.add(kee[len("project:"):])
        except Exception,e:
            # 表示没有当前数据库
            print "初始化数据库"

        # 读取所有项目
        projectIds = set()
        cursor_code.execute("select id from projects_project")
        projects = cursor_code.fetchall()
        for project in projects:
            id = project[0]
            projectIds.add(str(id))

        # 生成所有未处理的项目
        unhandledProjects = projectIds - handledProjects

        for project_id in unhandledProjects:
            cursor_code.execute("select id,name,path,code,project_id,file_index from projects_file where project_id=%s",(project_id,))
            blobs = cursor_code.fetchall()
            files = [] # 用来组装成一个project
            for blob in blobs:
                blob_id = blob[0]
                blob_name = blob[1]
                blob_path = blob[2]
                blob_code = blob[3]
                blob_project_id = blob[4]
                blob_file_index = blob[5]

                if blob_name == None or blob_path == None:
                    continue # 表示这个文件在数据库中的数据有问题,分析的时候不考虑这个文件了
                relPathIndex = str(blob_path).rfind(blob_name)
                if relPathIndex < 0:
                    continue # 表示这个文件在数据库中的数据有问题
                blob_relpath = blob_path[:relPathIndex]

                file = {"code":blob_code, "relPath":blob_relpath, "path":blob_path}
                files.append(file)

            projectKey = "project:" + str(project_id)
            projectName = "project:" + str(project_id)
            projectPath = utils.assemble("project:" + str(project_id), files)
            sonar_cmd = 'sonar-scanner -Dsonar.projectKey=' + projectKey + ' -Dsonar.projectName=' + projectName \
                    + ' -Dsonar.projectVersion=1.0 -Dsonar.sources=' + projectPath + \
                    ' -Dsonar.sourceEncoding=UTF-8'

            # 需要判断是不是执行成功了
            result = os.system(sonar_cmd)
            if result != 0:
                # 表示执行失败了
                print "执行失败_项目:" + str(project_id)
                os.system("rm -fr " + projectPath) # 删除临时拼接的工程
                continue
            else:
                print "执行成功_项目:" + str(project_id)
                os.system("rm -fr " + projectPath) # 删除临时拼接的工程

                # 转存数据
                moveResult(project_id, projectKey, projectName)
        
        for project_id in projectIds:
            # 查看sonar_results表中是不是有对应的数据
            cursor_code.execute("select * from sonar_results where project_id=%s",(project_id,))
            if len(cursor_code.fetchall()) == 0:
                # 表示没有对应的记录
                print "项目%s转存数据库出现了问题" % (project_id)
                projectKey = "project:" + str(project_id)
                projectName = "project:" + str(project_id)
                moveResult(project_id,projectKey,projectName)

        print "处理完了一批工程,休眠100秒..."
        time.sleep(100) # 表示每次处理之后休眠1000s
