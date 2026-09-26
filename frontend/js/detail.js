/* API 文档详情页：元信息 + 在线调试 + 响应示例 + 历史测试记录（全部走公开接口） */
const { createApp } = Vue;
const {
  METHODS, request, formatTime, prettyJson, parseJsonInput, copyText,
} = window.ApiClient;

function queryId() {
  return new URLSearchParams(window.location.search).get("id") || "";
}

createApp({
  data() {
    return {
      methods: METHODS,
      apiId: queryId(),
      api: null,
      records: [],
      test: { method: "GET", url: "", paramsText: "{}", bodyText: "{}" },
      testResult: null,
      testing: false,
      testError: "",
      loading: true,
      error: "",
      copied: "",
      copyTimer: null,
    };
  },

  computed: {
    examplePretty() {
      return prettyJson(this.api ? this.api.response_example : "");
    },
    testBody() {
      if (!this.testResult) return "";
      const body = this.testResult.response.body;
      if (!body) return this.testResult.response.error || "（无响应内容）";
      return prettyJson(body);
    },
  },

  mounted() {
    if (!this.apiId) {
      this.loading = false;
      this.error = "缺少 API 编号，请从列表页进入";
      return;
    }
    this.loadApi();
  },

  methods: {
    formatTime,

    async loadApi() {
      this.error = "";
      this.loading = true;
      try {
        const data = await request(`/public/apis/${this.apiId}`, { auth: false });
        this.api = data.api;
        document.title = `${this.api.name} · QQAPI`;
        this.test.method = this.api.method;
        this.test.url = this.api.full_url;
        await this.loadRecords();
      } catch (err) {
        this.error = err.message;
      } finally {
        this.loading = false;
      }
    },

    async loadRecords() {
      if (!this.api) return;
      try {
        const data = await request(`/public/apis/${this.api.id}/records`, { auth: false });
        this.records = data.items || [];
      } catch (err) {
        this.records = [];
      }
    },

    async sendTest() {
      this.testError = "";
      this.testResult = null;

      let params;
      let body;
      try {
        params = parseJsonInput(this.test.paramsText, {});
        body = parseJsonInput(this.test.bodyText, null);
      } catch (err) {
        this.testError = err.message;
        return;
      }
      if (typeof params !== "object" || params === null || Array.isArray(params)) {
        this.testError = "查询参数需要是 JSON 对象，例如 {\"q\": \"关键词\"}";
        return;
      }

      this.testing = true;
      try {
        this.testResult = await request(`/public/apis/${this.api.id}/test`, {
          auth: false,
          method: "POST",
          body: JSON.stringify({
            method: this.test.method,
            url: this.test.url,
            params,
            body,
          }),
        });
        await this.loadRecords();
      } catch (err) {
        this.testError = err.message;
      } finally {
        this.testing = false;
      }
    },

    async copy(text, field) {
      const ok = await copyText(text || "");
      if (!ok) {
        this.error = "复制失败，请手动选择文本复制";
        return;
      }
      this.copied = field;
      clearTimeout(this.copyTimer);
      this.copyTimer = setTimeout(() => {
        this.copied = "";
      }, 3000);
    },
  },
}).mount("#app");