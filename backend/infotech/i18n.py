TEXT = {
    'Website name':'网站名称', 'Website URL':'网址', 'Title':'标题', 'Body':'正文', 'Add link':'添加链接', 'Edit link':'编辑链接', 'Add tip':'添加小贴士', 'Edit tip':'编辑小贴士', 'Edit':'编辑', 'Add':'添加', 'No links yet':'暂无链接', 'No tips yet':'暂无小贴士', 'Use an HTTP or HTTPS URL.':'请输入 HTTP 或 HTTPS 网址。',
    'Guide':'指南', 'Course Recommendation':'课程推荐', 'Useful Links':'常用链接', 'Tips':'小贴士',
    'Name':'课程名称', 'Category':'类别', 'Exam Difficulty':'考试难度', 'Exam difficulty':'考试难度', 'Exam Form':'考试形式', 'Exam form':'考试形式',
    'Description':'说明', 'Semester':'学期', 'Capacity limited':'需要抢课', 'EE module':'EE 模块', 'CS module':'CS 模块',
    'Hard':'难', 'Medium':'中等', 'Simple':'简单', 'Open Book':'开卷', 'Close Book':'闭卷', 'Just Representation/Report':'展示／报告', 'Oral Exam':'口试',
    'Winter semester':'冬季学期', 'Summer semester':'夏季学期', 'Search courses':'搜索课程', 'All categories':'全部类别', 'All semesters':'全部学期',
    'Filter':'筛选', 'Reset':'重置', 'No courses yet':'暂无课程', 'No matching courses':'没有匹配的课程', 'Edit course':'编辑课程', 'Add course':'添加课程',
    'Select a course to edit':'选择课程后编辑', 'Cancel':'取消', 'Save changes':'保存修改', 'Password':'密码', 'Enter':'进入', 'Lock website':'退出',
    'Password incorrect':'密码错误', 'Course updated':'课程已更新', 'Course added':'课程已添加', 'Coming soon':'待添加', 'Enter a course name.':'请输入课程名称。',
}
def text(value, lang):
    return TEXT.get(value, value) if lang == 'zh' else value

