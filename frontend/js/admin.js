/* 后台管理页：管理员登录 + API 增删改，走 /api/admin/* 管理接口 */
const { createApp } = Vue;
const {
  METHODS, request, formatTime,
  getToken, setToken, clearToken,
} = window.ApiClient;

function emptyForm() {
  return {
    name: "",
    method: "GET",
    path: "",
    base_url: "",
    link: "",
    category: "",
    description: "",
    response_example: "",
    is_enabled: true,
  };
}

createApp({
  data() {
    return {
      methods: METHODS,
      token: getToken(),
      user: null,
      loginForm: { username: "", password: "" },
      form: emptyForm(),
      editingId: null,
      apis: [],
      total: 0,
      keyword: "",
      loading: false,
      error: "",
      info: "",
      infoTimer: null,
    };
  },

  mounted() {
    if (this.token) this.bootstrap();
  },

  methods: {
    formatTime,

    async bootstrap() {
      try {
        const data = await request("/auth/me");
        this.user = data.user;
        if (!this.user.is_admin) {
          this.logout();
          this.error = "该账号没有管理权限";
          return;
        }
        await this.loadApis();
      } catch (err) {
        this.logout();
        this.error = err.message;
      }
    },

    async login() {
      this.error = "";
      if (!this.loginForm.username || !this.loginForm.password) {
        this.error = "请输入用户名和密码";
        return;
      }
      this.loading = true;
      try {
        const data = await request("/auth/login", {
          auth: false,
          method: "POST",
          body: JSON.stringify(this.loginForm),
        });
        setToken(data.token);
        this.token = data.token;
        this.user = data.user;
        this.loginForm = { username: "", password: "" };
        this.showInfo(data.message);
        await this.loadApis();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    logout(silent) {
      clearToken();
      this.token = "";
      this.user = null;
      this.apis = [];
      this.total = 0;
      this.keyword = "";
      this.resetForm();
      if (silent !== true) this.showInfo("已退出登录");
    },

    async loadApis() {
      this.error = "";
      try {
        const q = this.keyword ? "?q=" + encodeURIComponent(this.keyword) : "";
        const data = await request("/admin/apis" + q);
        this.apis = data.items || [];
        this.total = data.total || 0;
      } catch (err) {
        this.error = err.message;
      }
    },

    async save() {
      this.error = "";
      if (!this.form.name || !this.form.path) {
        this.error = "名称和请求路径不能为空";
        return;
      }

      this.loading = true;
      const isEdit = this.editingId !== null;
      try {
        const data = await request(
          isEdit ? `/admin/apis/${this.editingId}` : "/admin/apis",
          { method: isEdit ? "PUT" : "POST", body: JSON.stringify(this.form) }
        );
        this.resetForm();
        this.showInfo(data.message);
        await this.loadApis();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    edit(api) {
      this.error = "";
      this.editingId = api.id;
      this.form = {
        name: api.name,
        method: api.method,
        path: api.path,
        base_url: api.base_url || "",
        link: api.link || "",
        category: api.category || "",
        description: api.description || "",
        response_example: api.response_example || "",
        is_enabled: api.is_enabled,
      };
      window.scrollTo({ top: 0, behavior: "smooth" });
    },

    resetForm() {
      this.editingId = null;
      this.form = emptyForm();
    },

    async toggleStatus(api) {
      const action = api.is_enabled ? "下架" : "上架";
      this.error = "";
      try {
        const data = await request(`/admin/apis/${api.id}/status`, {
          method: "PUT",
          body: JSON.stringify({ is_enabled: !api.is_enabled }),
        });
        this.showInfo(data.message || `已${action}`);
        await this.loadApis();
      } catch (err) {
        this.error = err.message;
      }
    },

    async remove(api) {
      if (!window.confirm(`确定删除「${api.name}」吗？该 API 的历史测试记录也会一并删除。`)) return;

      this.error = "";
      try {
        const data = await request(`/admin/apis/${api.id}`, { method: "DELETE" });
        if (this.editingId === api.id) this.resetForm();
        this.showInfo(data.message);
        await this.loadApis();
      } catch (err) {
        this.error = err.message;
      }
    },

    async clearRecords(api) {
      if (!window.confirm(`确定清空「${api.name}」的全部历史测试记录吗？`)) return;

      this.error = "";
      try {
        const data = await request(`/admin/apis/${api.id}/records`, { method: "DELETE" });
        this.showInfo(data.message);
      } catch (err) {
        this.error = err.message;
      }
    },

    showInfo(message) {
      this.info = message;
      clearTimeout(this.infoTimer);
      this.infoTimer = setTimeout(() => {
        this.info = "";
      }, 2500);
    },
  },
}).mount("#app");