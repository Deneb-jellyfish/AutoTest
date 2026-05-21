package com.zdmj.common.exception;

import lombok.Getter;

/**
 * 统一错误码定义
 * 用于统一管理业务错误码
 */
@Getter
public enum ErrorCode {

    // ========== HTTP状态码 ==========
    BAD_REQUEST(400, "请求参数错误"),
    INTERNAL_ERROR(500, "服务器内部错误"),

    // ========== 通用错误 1xxx ==========
    VALIDATION_ERROR(1001, "参数校验失败"),
    USER_NOT_LOGIN(1002, "用户未登录"),
    NO_PERMISSION(1003, "无权操作"),
    REQUEST_BODY_ERROR(1004, "请求体错误，请提供有效的JSON数据"),
    DATE_FORMAT_ERROR(1005, "日期格式错误，请使用 yyyy-MM-dd 格式（例如：2024-09-01）"),
    URL_FORMAT_ERROR(1007, "URL格式不正确"),
    SYSTEM_EXCEPTION(1008, "系统异常，请联系管理员"),
    FILE_EMPTY(1009, "上传文件不能为空"),

    // ========== 用户相关 (2xxx) ==========
    USER_ALREADY_EXISTS(2001, "用户名已存在"),
    USER_EMAIL_EXISTS(2002, "邮箱已被注册"),
    CAPTCHA_ERROR(2003, "验证码错误或已过期"),
    USER_REGISTER_FAILED(2004, "用户注册失败"),
    USER_PASSWORD_WRONG(2005, "用户名或密码错误"),
    USER_NOT_FOUND(2006, "用户不存在"),
    USER_EMAIL_NOT_REGISTERED(2007, "该邮箱未注册"),
    PASSWORD_CHANGE_FAILED(2008, "密码修改失败"),
    CAPTCHA_SEND_FAILED(2009, "验证码发送失败，请稍后重试"),

    // ========== 简历相关 (3xxx) ==========
    RESUME_NAME_EXISTS(3001, "简历名称已存在，请使用其他名称"),
    RESUME_CREATE_FAILED(3002, "创建简历失败"),
    RESUME_UPDATE_FAILED(3004, "更新简历失败"),
    RESUME_DELETE_FAILED(3005, "删除简历失败"),
    RESUME_NOT_FOUND(3006, "简历不存在"),

    // ========== 项目经历相关 (4xxx) ==========
    PROJECT_EXPERIENCE_ADD_FAILED(4001, "添加项目经历失败"),
    PROJECT_END_TIME_INVALID(4002, "项目结束时间不能早于开始时间"),
    PROJECT_EXPERIENCE_UPDATE_FAILED(4003, "更新项目经历失败"),
    PROJECT_EXPERIENCE_DELETE_FAILED(4004, "删除项目经历失败"),
    PROJECT_EXPERIENCE_NOT_FOUND(4005, "项目经历不存在"),

    // ========== 工作经历相关 (5xxx) ==========
    CAREER_ADD_FAILED(5001, "添加工作经历失败"),
    CAREER_LEAVE_TIME_INVALID(5003, "离职时间不能早于入职时间"),
    CAREER_UPDATE_FAILED(5004, "更新工作经历失败"),
    CAREER_DELETE_FAILED(5005, "删除工作经历失败"),
    CAREER_NOT_FOUND(5006, "工作经历不存在"),

    // ========== 教育经历相关 (6xxx) ==========
    EDUCATION_ADD_FAILED(6001, "添加教育经历失败"),
    EDUCATION_UPDATE_FAILED(6002, "更新教育经历失败"),
    EDUCATION_GRADUATE_TIME_INVALID(6003, "毕业时间不能早于入学时间"),
    EDUCATION_DELETE_FAILED(6004, "删除教育经历失败"),
    EDUCATION_NOT_FOUND(6005, "教育经历不存在"),

    // ========== 技能相关 (7xxx) ==========
    SKILL_ADD_FAILED(7001, "添加技能失败"),
    SKILL_UPDATE_FAILED(7003, "更新技能失败"),
    SKILL_DELETE_FAILED(7004, "删除技能失败"),
    SKILL_NOT_FOUND(7005, "技能不存在"),

    // ========== 知识库相关 (8xxx) ==========
    KNOWLEDGE_BASE_SAVE_FAILED(8001, "保存知识库失败"),
    KNOWLEDGE_BASE_DELETE_FAILED(8004, "删除知识库失败"),
    KNOWLEDGE_BASE_NOT_FOUND(8005, "知识库不存在"),
    FILE_TYPE_NOT_EXISTS(8009, "文件类型不存在，请不要修改知识内容中的URL"),
    KNOWLEDGE_BASE_EMBEDDING_FAILED(8010, "向量化任务失败"),
    KNOWLEDGE_DOCUMENT_CREATE_FAILED(8011, "创建知识文档失败"),
    KNOWLEDGE_DOCUMENT_NOT_FOUND(8012, "知识文档不存在"),
    KNOWLEDGE_DOCUMENT_UPDATE_FAILED(8013, "更新知识文档失败"),

    // ========== 对话相关 (9xxx) ==========
    CONVERSATION_CREATE_FAILED(9001, "创建会话失败"),
    CONVERSATION_DELETE_FAILED(9002, "删除会话失败"),
    CONVERSATION_NOT_FOUND(9003, "会话不存在"),
    CONVERSATION_UPDATE_FAILED(9004, "更新会话失败"),
    MESSAGE_CREATE_FAILED(9005, "创建消息失败"),

    // ========== 岗位与公司 (82xx) ==========
    JOB_NOT_FOUND(8201, "岗位不存在"),
    JOB_CAPABILITY_PROFILE_GENERATION_FAILED(8202, "生成岗位能力画像失败"),
    JOB_DETECT_FAILED(8203, "岗位分类失败"),
    JOB_CAREER_GRAPH_GENERATION_FAILED(8204, "生成岗位关联图谱失败"),
    JOB_CAREER_GRAPH_INVALID(8205, "岗位关联图谱结果不符合要求（晋升路径或换岗路径数量不足）"),

    // ========== 人岗匹配 (83xx) ==========
    MATCH_GENERATION_FAILED(8301, "生成人岗匹配分析失败，请稍后重试"),
    MATCH_PRECONDITION_MISSING(8302, "学生能力画像缺失，请先到能力画像页生成画像"),
    MATCH_NOT_FOUND(8303, "人岗匹配分析不存在"),
    MATCH_WEIGHTS_INVALID(8304, "权重配置不合法"),

    // ========== 职业发展报告 (84xx) ==========
    CAREER_REPORT_NOT_FOUND(8401, "职业发展报告不存在"),
    CAREER_REPORT_GENERATION_FAILED(8402, "生成职业发展报告失败，请稍后重试"),
    CAREER_REPORT_POLISH_FAILED(8403, "润色职业发展报告失败，请稍后重试"),
    CAREER_REPORT_INVALID(8404, "职业发展报告结果不符合要求");

    private final Integer code;
    private final String message;

    ErrorCode(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}
