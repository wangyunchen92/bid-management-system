/** 统一 API 响应 */
interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
  timestamp: number;
}

/** 分页响应 */
interface PaginatedData<T = unknown> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/** 当前用户 */
interface CurrentUser {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  role: string;
  permissions: string[];
}

/** 登录参数 */
interface LoginParams {
  username: string;
  password: string;
}

/** 登录结果 */
interface LoginResult {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** 字典类型 */
interface DictType {
  id: number;
  dict_name: string;
  dict_code: string;
  description?: string;
  status: number;
  created_at?: string;
}

/** 字典项 */
interface DictItem {
  id: number;
  dict_type_id: number;
  item_label: string;
  item_value: string;
  sort_order: number;
  status: number;
  description?: string;
}

/** 部门 */
interface Department {
  id: number;
  dept_name: string;
  dept_code: string;
  parent_id?: number;
  leader_id?: number;
  sort_order: number;
  status: number;
  created_at?: string;
  children?: Department[];
}

/** 用户角色信息 */
interface UserRoleInfo {
  role_id: number;
  role_name: string;
  role_code: string;
}

/** 系统用户 */
interface SystemUser {
  id: number;
  username: string;
  real_name: string;
  phone?: string;
  email?: string;
  avatar?: string;
  dept_id?: number;
  dept_name?: string;
  position?: string;
  role: string;
  status: number;
  last_login_at?: string;
  created_at?: string;
  roles?: UserRoleInfo[];
}

/** 角色 */
interface SysRole {
  id: number;
  role_name: string;
  role_code: string;
  description?: string;
  sort_order: number;
  status: number;
  created_at?: string;
}

/** 审批实例 */
interface ApprovalInstance {
  id: number;
  title: string;
  biz_type: string;
  biz_id?: number;
  initiator_id: number;
  initiator_name?: string;
  approver_id: number;
  approver_name?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  result_comment?: string;
  approved_at?: string;
  created_at?: string;
}

/** 审批记录 */
interface ApprovalRecord {
  id: number;
  instance_id: number;
  operator_id: number;
  operator_name?: string;
  action: 'SUBMIT' | 'APPROVE' | 'REJECT' | 'TRANSFER';
  comment?: string;
  created_at?: string;
}

/** 审批详情 */
interface ApprovalDetail {
  instance: ApprovalInstance;
  records: ApprovalRecord[];
}

/** 招标信息 */
interface Tender {
  id: number;
  title: string;
  tender_no?: string;
  tender_unit?: string;
  tender_method?: string;
  info_source?: string;
  province?: string;
  city?: string;
  budget_amount?: number;
  deposit_amount?: number;
  deposit_deadline?: string;
  reg_deadline?: string;
  open_bid_time?: string;
  status: string;
  follower_id?: number;
  follower_name?: string;
  remark?: string;
  created_at?: string;
}

/** 日历项 */
interface TenderCalendarItem {
  id: number;
  title: string;
  date: string;
  type: 'reg_deadline' | 'deposit_deadline' | 'open_bid';
  label: string;
}

/** 统计 */
interface TenderStats {
  total: number;
  pending: number;
  decided_bid: number;
  decided_give_up: number;
  composing: number;
  submitted: number;
  opened: number;
}

/** 开标记录 */
interface BidOpening {
  id: number;
  tender_id: number;
  tender_title?: string;
  tender_no?: string;
  opening_time?: string;
  result?: string;
  our_price?: number;
  win_price?: number;
  win_company?: string;
  total_bidders?: number;
  ranking?: number;
  review_summary?: string;
  lessons_learned?: string;
  remark?: string;
  created_at?: string;
}

/** 资质证书 */
interface Qualification {
  id: number;
  cert_name: string;
  cert_type?: string;
  cert_no?: string;
  issuing_authority?: string;
  issue_date?: string;
  expiry_date?: string;
  status: number;
  remark?: string;
  created_at?: string;
}

/** 业绩案例 */
interface Achievement {
  id: number;
  project_name: string;
  client_name?: string;
  contract_amount?: number;
  completion_date?: string;
  project_type?: string;
  description?: string;
  remark?: string;
  created_at?: string;
}

/** 人员证书 */
interface PersonnelCert {
  id: number;
  person_name: string;
  cert_name: string;
  cert_no?: string;
  cert_type?: string;
  issue_date?: string;
  expiry_date?: string;
  status: number;
  remark?: string;
  created_at?: string;
}

/** 产品/设备 */
interface Product {
  id: number;
  name: string;
  model?: string;
  brand?: string;
  quantity: number;
  unit?: string;
  description?: string;
  remark?: string;
  created_at?: string;
}

/** 标书项目 */
interface BidProject {
  id: number;
  tender_id?: number;
  tender_title?: string;
  title: string;
  doc_type?: string;
  status: string;
  deadline?: string;
  leader_id?: number;
  leader_name?: string;
  section_count: number;
  remark?: string;
  created_at?: string;
}

/** 标书章节 */
interface BidSection {
  id: number;
  project_id: number;
  parent_id?: number;
  title: string;
  content?: string;
  sort_order: number;
  assignee_id?: number;
  assignee_name?: string;
  status: string;
  word_count: number;
  children?: BidSection[];
}

/** 招标文件解析结果 */
interface TenderDocumentInfo {
  id: number;
  project_id?: number;
  tender_id?: number;
  original_name: string;
  file_size: number;
  file_type: string;
  page_count?: number;
  parse_status: 'PENDING' | 'EXTRACTING' | 'PARSING' | 'COMPLETED' | 'FAILED';
  parse_result?: TenderParseResult;
  error_message?: string;
  created_at?: string;
}

interface TenderParseResult {
  basic_info?: {
    project_name?: string;
    tender_no?: string;
    tender_unit?: string;
    agent_unit?: string;
    tender_method?: string;
    budget_amount?: number;
    budget_amount_text?: string;
  };
  timeline?: {
    publish_date?: string;
    question_deadline?: string;
    bid_deadline?: string;
    open_bid_time?: string;
    open_bid_place?: string;
    deposit_amount?: number;
    deposit_amount_text?: string;
    deposit_deadline?: string;
  };
  qualification?: {
    required_certs?: string[];
    required_experience?: string;
    team_requirements?: string;
    financial_requirements?: string;
    exclusion_conditions?: string[];
  };
  scoring?: {
    method?: string;
    technical_score?: number;
    commercial_score?: number;
    price_score?: number;
    details?: { category?: string; item?: string; max_score?: number; criteria?: string }[];
  };
  bid_document_requirements?: {
    format?: string;
    copies?: string;
    seal_requirements?: string;
    chapters?: string[];
  };
  risk_alerts?: string[];
}

/** 废标检查项 */
interface BidCheckItem {
  requirement: string;
  status: 'PASS' | 'WARN' | 'FAIL';
  detail: string;
  suggestion?: string;
}

/** 废标检查结果 */
interface BidCheckResult {
  overall_status: string;
  score: number;
  pass: boolean;
  items: BidCheckItem[];
  missing_sections?: string[];
  risk_warnings?: string[];
}

/** 投标决策 */
interface BidDecision {
  id: number;
  tender_id: number;
  tender_title?: string;
  tender_no?: string;
  decision_reason?: string;
  risk_analysis?: string;
  estimated_amount?: number;
  win_probability?: number;
  competitors?: string;
  decision_result: string;
  approval_id?: number;
  approval_status?: string;
  initiator_id: number;
  initiator_name?: string;
  remark?: string;
  created_at?: string;
}
