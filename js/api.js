/* 前台与后台共用的 API 客户端与工具方法 */
(function (global) {
  // 前后端同源部署（本地也由 Flask 托管前端），用相对路径即可
  var API_BASE = "/api";
  var TOKEN_KEY = "qqapi_token";
  var METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"];

  function getToken() {
    return localStorage.getItem(TOKEN_KEY) || "";
  }
  function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
  }
  function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
  }

  /**
   * 统一请求封装。
   * auth: false 表示这是公开接口，不带 Token（前台全部走公开接口）。
   */
  function request(path, options) {
    options = options || {};
    var headers = Object.assign(
      { "Content-Type": "application/json" },
      options.headers || {}
    );
    var withAuth = options.auth !== false;
    if (withAuth && getToken()) {
      headers.Authorization = "Bearer " + getToken();
    }

    return fetch(API_BASE + path, Object.assign({}, options, { headers: headers }))
      .catch(function () {
        throw new Error("无法连接后端服务，请确认后端已启动");
      })
      .then(function (res) {
        return res
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            if (res.status === 401 && withAuth) clearToken();
            if (!res.ok) {
              var err = new Error(data.message || "请求失败（" + res.status + "）");
              err.status = res.status;
              throw err;
            }
            return data;
          });
      });
  }

  function formatTime(iso) {
    if (!iso) return "-";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    var p = function (n) {
      return String(n).padStart(2, "0");
    };
    return (
      d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) +
      " " + p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds())
    );
  }

  /** 把 JSON 字符串格式化成易读形式；不是合法 JSON 就原样返回 */
  function prettyJson(text) {
    if (!text) return "";
    try {
      return JSON.stringify(JSON.parse(text), null, 2);
    } catch (e) {
      return text;
    }
  }

  /** 解析用户输入的 JSON 文本，空文本返回 emptyValue */
  function parseJsonInput(text, emptyValue) {
    var raw = (text || "").trim();
    if (!raw) return emptyValue;
    try {
      return JSON.parse(raw);
    } catch (e) {
      throw new Error("输入的 JSON 格式有误：" + e.message);
    }
  }

  /** 一键复制。优先用剪贴板 API，不可用时回退到 execCommand */
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).then(
        function () { return true; },
        function () { return legacyCopy(text); }
      );
    }
    return Promise.resolve(legacyCopy(text));
  }

  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try {
      ok = document.execCommand("copy");
    } catch (e) {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  global.ApiClient = {
    API_BASE: API_BASE,
    METHODS: METHODS,
    getToken: getToken,
    setToken: setToken,
    clearToken: clearToken,
    request: request,
    formatTime: formatTime,
    prettyJson: prettyJson,
    parseJsonInput: parseJsonInput,
    copyText: copyText,
  };
})(window);