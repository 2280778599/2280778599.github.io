/* 前台首页：公开 API 卡片列表（无需登录，只读） */
const { createApp } = Vue;
const { request, formatTime } = window.ApiClient;

createApp({
  data() {
    return {
      apis: [],
      total: 0,
      categories: [],
      keyword: "",
      filterCategory: "",
      loading: false,
      error: "",
    };
  },

  mounted() {
    this.loadCategories();
    this.loadApis();
  },

  methods: {
    formatTime,

    async loadCategories() {
      try {
        const data = await request("/public/categories", { auth: false });
        this.categories = data.items || [];
      } catch (err) {
        /* 分类获取失败不影响主流程 */
      }
    },

    async loadApis() {
      this.error = "";
      this.loading = true;
      try {
        const params = new URLSearchParams();
        if (this.keyword) params.set("q", this.keyword);
        if (this.filterCategory) params.set("category", this.filterCategory);
        const query = params.toString();

        const data = await request(
          "/public/apis" + (query ? "?" + query : ""),
          { auth: false }
        );
        this.apis = data.items || [];
        this.total = data.total || 0;
      } catch (err) {
        this.error = err.message;
        this.apis = [];
        this.total = 0;
      } finally {
        this.loading = false;
      }
    },
  },
}).mount("#app");