const savedLanguage = localStorage.getItem("red-lan-sync-language");

const state = {
  overview: null,
  audit: null,
  activeJob: null,
  pairing: null,
  updateInfo: null,
  polling: false,
  currentTab: "overview",
  lang: savedLanguage || ((navigator.language || "").toLowerCase().startsWith("zh") ? "zh" : "en"),
};

const i18n = {
  zh: {
    navOverview: "总览",
    navNaming: "命名检查",
    navDevices: "设备",
    navStorage: "存储",
    navPairing: "配对",
    syncthingLink: "Syncthing 管理页 ↗",
    languageLabel: "语言",
    pageOverview: "同步总览",
    pageNaming: "工程命名检查",
    pageDevices: "设备与唤醒",
    pageStorage: "存储位置",
    pagePairing: "新设备配对",
    summaryCompletion: "同步完成度",
    summaryNeed: "待同步",
    summaryConnection: "连接方式",
    summaryFolder: "文件夹状态",
    devicePairStatus: "双端状态",
    idleTime: "空闲时间",
    systemLabel: "系统",
    companionAgent: "伴随代理",
    lastOnline: "最后在线",
    recentJobs: "最近任务",
    emptyJobs: "当前没有后台任务",
    namingTitle: "工程命名审计",
    sourceUntouched: "原文件不改动",
    sourceFolder: "源工程文件夹",
    normalizedCopy: "规范化副本位置",
    keepSpaces: "保留空格",
    scanNames: "扫描命名",
    createSafeCopy: "创建安全副本",
    resumeSync: "继续当前同步",
    resumeSyncHint: "恢复暂停项并重新扫描当前同步文件夹",
    quickSyncTitle: "新增同步文件夹",
    quickSyncHint: "为新工程同时指定 Mac 与 Windows 端路径",
    useNormalizedCopy: "使用规范化副本路径",
    addSyncFolder: "新增同步文件夹",
    auditTotal: "扫描条目",
    auditRenamed: "需要改名",
    auditCollisions: "冲突消解",
    auditSkipped: "跳过",
    originalPath: "原路径",
    safePath: "规范路径",
    reason: "原因",
    powerTitle: "设备电源状态",
    wakeRemote: "唤醒 Red5090",
    powerBoundaryTitle: "电源边界",
    powerBoundaryBody: "没有伴随代理时，休眠、关机与网络断开只能显示为“离线/未知”。两台电脑同时休眠时，没有在线设备可发送唤醒包。",
    windowsIp: "Windows IP",
    windowsMac: "Windows MAC",
    directConnection: "Syncthing 直连",
    agentPort: "伴随代理端口",
    storageTitle: "磁盘与工程位置",
    loading: "读取中",
    needsWindowsAgent: "需要 Windows 伴随代理",
    windowsProjectBase: "Windows 默认工程根目录",
    saveTarget: "保存目标位置",
    registerProjectTitle: "注册独立工程",
    macProjectPath: "Mac 工程路径",
    folderId: "文件夹 ID",
    displayName: "显示名称",
    windowsProjectPath: "Windows 工程路径",
    registerSyncthing: "注册到双端 Syncthing",
    pairingTitle: "新设备加入",
    controllerAccess: "控制台入口",
    copyLanUrl: "复制局域网地址",
    copyDeviceId: "复制本机设备 ID",
    sharedFolder: "共享文件夹",
    folderPath: "本机路径",
    deviceId: "本机设备 ID",
    approveDeviceTitle: "添加并共享给新设备",
    newDeviceName: "新设备名称",
    newDeviceAddress: "连接地址",
    newDeviceId: "Syncthing 设备 ID",
    addDeviceButton: "添加设备并共享 lan-sync",
    knownDevices: "已知设备",
    pendingDevices: "待确认设备",
    nonePending: "暂无待确认设备",
    mobileLimitTitle: "手机说明",
    mobileLimitBody: "Android 可以通过 Syncthing 客户端加入同步；iPhone/iPad 通常只能打开这个控制台查看和触发操作，iOS 不适合做常驻 Syncthing 文件节点。",
    refreshNow: "立即刷新",
    refreshDisks: "刷新磁盘",
    refreshPairing: "刷新配对信息",
    online: "在线",
    idle: "待机",
    sleeping: "休眠",
    powered_off: "已关机",
    offline_unknown: "离线/未知",
    offline: "离线",
    unknown: "未知",
    serviceOnline: "服务在线",
    syncthingError: "Syncthing 异常",
    controlServiceError: "控制服务异常",
    healthHealthy: "已同步",
    healthSyncing: "正在同步",
    healthWaiting: "等待远端",
    healthStalled: "同步未继续",
    healthPaused: "已暂停",
    healthError: "同步异常",
    healthUnavailable: "服务不可用",
    healthUnknown: "状态未知",
    healthHealthyDetail: "当前文件夹已同步完成",
    healthSyncingDetail: "正在同步，剩余 {bytes}",
    healthWaitingDetail: "未连接到远端，无法继续同步",
    healthStalledDetail: "还有 {bytes} 未同步，但文件夹处于空闲；请检查另一端是否暂停、缺失文件或未扫描",
    healthPausedDetail: "当前文件夹或设备已暂停",
    healthErrorDetail: "Syncthing 报告 {count} 个错误",
    healthUnavailableDetail: "Syncthing API 当前不可用",
    lanDirect: "局域网直连",
    relayWan: "中继/广域网",
    disconnected: "未连接",
    waitingForRemote: "等待 Red5090 连接",
    syncthingApi: "Syncthing API：{error}",
    connectedAddress: "已连接 {address}",
    companionConnected: "已连接",
    companionDisconnected: "未连接",
    updatedAt: "更新于 {time}",
    noRemoteSeen: "未记录",
    durationSeconds: "{value} 秒",
    durationMinutes: "{value} 分钟",
    durationHours: "{hours} 小时 {minutes} 分钟",
    localStatusLoading: "读取本机状态",
    remoteStatusWaiting: "等待远端响应",
    noLocalDisks: "未找到本机磁盘",
    freeDisk: "{free} 可用 / {total}",
    busyScanning: "扫描中",
    busySubmitted: "任务已提交",
    busySending: "正在发送",
    busySaving: "保存中",
    busyRegistering: "注册中",
    busyAdding: "添加中",
    busyResuming: "继续中",
    auditComplete: "扫描完成：{count} 个条目需要规范化",
    noRenameNeeded: "没有发现需要修改的文件名",
    safeCopyDone: "安全副本与检查报告已完成",
    copyFailed: "创建副本失败",
    wakeSent: "唤醒包已发送：{targets}",
    resumeDone: "已请求继续同步，并重新扫描当前文件夹",
    resumeLocalOnly: "本机已继续同步；Windows 伴随代理暂时不可用",
    targetSaved: "Windows 默认工程位置已更新",
    projectRegistered: "工程 {folder} 已注册到双端",
    quickPathCopied: "已使用规范化副本路径",
    copied: "已复制",
    copyAction: "复制",
    pairingLoaded: "配对信息已刷新",
    deviceAdded: "设备 {name} 已加入并共享 {folder}",
    pendingUse: "填入",
    dynamicAddress: "dynamic",
    noKnownDevices: "暂无已知设备",
    companionPackage: "Windows 安装包：{path}",
    mobileAccess: "手机可打开同一局域网地址查看控制台",
    remoteDetailCompanion: "伴随代理已连接",
    remoteDetailSyncthing: "Syncthing 已连接；伴随代理不可用",
    remoteDetailSleep: "最后电源事件为休眠",
    remoteDetailShutdown: "最后电源事件为正常关机",
    remoteDetailUnknown: "没有伴随心跳时，无法区分关机、休眠或网络断开",
    unicode_normalized_nfc: "Unicode 统一",
    windows_invalid_chars: "Windows 禁用字符",
    whitespace_to_underscore: "空格规范化",
    trimmed_edge_space_or_dot: "末尾空格/句点",
    empty_or_dot_name: "空文件名",
    windows_reserved_name: "Windows 保留名",
    segment_truncated: "名称过长",
    updatePreviewBadge: "更新预览",
    viewUpdate: "查看 GitHub 更新",
    updateBubbleTitle: "开发者发布了新的工具架构：{version}",
    updateBubblePreviewFallback: "打开 GitHub 查看此版本的更新说明。",
  },
  en: {
    navOverview: "Overview",
    navNaming: "Name Audit",
    navDevices: "Devices",
    navStorage: "Storage",
    navPairing: "Pairing",
    syncthingLink: "Syncthing Console ↗",
    languageLabel: "Language",
    pageOverview: "Sync Overview",
    pageNaming: "Project Name Audit",
    pageDevices: "Devices & Wake",
    pageStorage: "Storage Targets",
    pagePairing: "Pair New Device",
    summaryCompletion: "Completion",
    summaryNeed: "To Sync",
    summaryConnection: "Connection",
    summaryFolder: "Folder State",
    devicePairStatus: "Device Status",
    idleTime: "Idle Time",
    systemLabel: "System",
    companionAgent: "Companion",
    lastOnline: "Last Online",
    recentJobs: "Recent Jobs",
    emptyJobs: "No background jobs",
    namingTitle: "Project Name Audit",
    sourceUntouched: "Source unchanged",
    sourceFolder: "Source Project Folder",
    normalizedCopy: "Normalized Copy Location",
    keepSpaces: "Keep spaces",
    scanNames: "Scan Names",
    createSafeCopy: "Create Safe Copy",
    resumeSync: "Resume Current Sync",
    resumeSyncHint: "Resume paused items and rescan the current sync folder",
    quickSyncTitle: "Add Sync Folder",
    quickSyncHint: "Set both Mac and Windows paths for a new project",
    useNormalizedCopy: "Use Normalized Copy Path",
    addSyncFolder: "Add Sync Folder",
    auditTotal: "Scanned Items",
    auditRenamed: "Needs Rename",
    auditCollisions: "Collisions",
    auditSkipped: "Skipped",
    originalPath: "Original Path",
    safePath: "Safe Path",
    reason: "Reason",
    powerTitle: "Power State",
    wakeRemote: "Wake Red5090",
    powerBoundaryTitle: "Power Limits",
    powerBoundaryBody: "Without the companion agent, sleep, shutdown, and network loss can only be shown as offline/unknown. If both computers sleep, no online device can send the wake packet.",
    windowsIp: "Windows IP",
    windowsMac: "Windows MAC",
    directConnection: "Syncthing Direct",
    agentPort: "Companion Port",
    storageTitle: "Disks & Project Location",
    loading: "Loading",
    needsWindowsAgent: "Windows companion required",
    windowsProjectBase: "Default Windows Project Root",
    saveTarget: "Save Target",
    registerProjectTitle: "Register Separate Project",
    macProjectPath: "Mac Project Path",
    folderId: "Folder ID",
    displayName: "Display Name",
    windowsProjectPath: "Windows Project Path",
    registerSyncthing: "Register in Syncthing",
    pairingTitle: "Join a New Device",
    controllerAccess: "Controller Access",
    copyLanUrl: "Copy LAN URL",
    copyDeviceId: "Copy Device ID",
    sharedFolder: "Shared Folder",
    folderPath: "Local Path",
    deviceId: "Local Device ID",
    approveDeviceTitle: "Add and Share to Device",
    newDeviceName: "New Device Name",
    newDeviceAddress: "Connection Address",
    newDeviceId: "Syncthing Device ID",
    addDeviceButton: "Add Device and Share lan-sync",
    knownDevices: "Known Devices",
    pendingDevices: "Pending Devices",
    nonePending: "No pending devices",
    mobileLimitTitle: "Mobile Note",
    mobileLimitBody: "Android can join sync with a Syncthing client. iPhone/iPad can usually open this controller for monitoring and actions, but iOS is not suitable as an always-on Syncthing file node.",
    refreshNow: "Refresh now",
    refreshDisks: "Refresh disks",
    refreshPairing: "Refresh pairing info",
    online: "Online",
    idle: "Idle",
    sleeping: "Sleeping",
    powered_off: "Powered Off",
    offline_unknown: "Offline/Unknown",
    offline: "Offline",
    unknown: "Unknown",
    serviceOnline: "Service online",
    syncthingError: "Syncthing error",
    controlServiceError: "Controller error",
    healthHealthy: "Synced",
    healthSyncing: "Syncing",
    healthWaiting: "Waiting for remote",
    healthStalled: "Sync blocked",
    healthPaused: "Paused",
    healthError: "Sync error",
    healthUnavailable: "Service unavailable",
    healthUnknown: "Unknown state",
    healthHealthyDetail: "Current folder is fully synced",
    healthSyncingDetail: "Syncing with {bytes} remaining",
    healthWaitingDetail: "Remote is disconnected, so sync cannot continue",
    healthStalledDetail: "{bytes} remain, but the folder is idle; check whether the other side is paused, missing files, or not scanned",
    healthPausedDetail: "The current folder or device is paused",
    healthErrorDetail: "Syncthing reports {count} errors",
    healthUnavailableDetail: "Syncthing API is currently unavailable",
    lanDirect: "LAN direct",
    relayWan: "Relay/WAN",
    disconnected: "Disconnected",
    waitingForRemote: "Waiting for Red5090",
    syncthingApi: "Syncthing API: {error}",
    connectedAddress: "Connected {address}",
    companionConnected: "Connected",
    companionDisconnected: "Disconnected",
    updatedAt: "Updated {time}",
    noRemoteSeen: "Not recorded",
    durationSeconds: "{value} sec",
    durationMinutes: "{value} min",
    durationHours: "{hours} hr {minutes} min",
    localStatusLoading: "Reading local state",
    remoteStatusWaiting: "Waiting for remote",
    noLocalDisks: "No local disks found",
    freeDisk: "{free} free / {total}",
    busyScanning: "Scanning",
    busySubmitted: "Submitted",
    busySending: "Sending",
    busySaving: "Saving",
    busyRegistering: "Registering",
    busyAdding: "Adding",
    busyResuming: "Resuming",
    auditComplete: "Scan complete: {count} items need normalization",
    noRenameNeeded: "No filenames need changes",
    safeCopyDone: "Safe copy and reports are complete",
    copyFailed: "Copy failed",
    wakeSent: "Wake packet sent: {targets}",
    resumeDone: "Sync resume requested and current folder scan started",
    resumeLocalOnly: "Local sync resumed; Windows companion is currently unavailable",
    targetSaved: "Default Windows project location updated",
    projectRegistered: "Project {folder} registered on both devices",
    quickPathCopied: "Normalized copy path applied",
    copied: "Copied",
    copyAction: "Copy",
    pairingLoaded: "Pairing info refreshed",
    deviceAdded: "Device {name} added and shared with {folder}",
    pendingUse: "Use",
    dynamicAddress: "dynamic",
    noKnownDevices: "No known devices",
    companionPackage: "Windows package: {path}",
    mobileAccess: "Phones can open the same LAN URL to use this controller",
    remoteDetailCompanion: "Companion agent connected",
    remoteDetailSyncthing: "Syncthing connected; companion agent unavailable",
    remoteDetailSleep: "Last power event reported sleep",
    remoteDetailShutdown: "Last power event reported normal shutdown",
    remoteDetailUnknown: "Cannot distinguish shutdown, sleep, or network loss without companion heartbeat",
    unicode_normalized_nfc: "Unicode normalized",
    windows_invalid_chars: "Windows invalid characters",
    whitespace_to_underscore: "Whitespace normalized",
    trimmed_edge_space_or_dot: "Trailing space/dot",
    empty_or_dot_name: "Empty name",
    windows_reserved_name: "Windows reserved name",
    segment_truncated: "Name too long",
    updatePreviewBadge: "Update Preview",
    viewUpdate: "View GitHub Update",
    updateBubbleTitle: "Developer published a new tool architecture: {version}",
    updateBubblePreviewFallback: "Open GitHub to view the release notes.",
  },
};

const pageTitleKeys = {
  overview: "pageOverview",
  naming: "pageNaming",
  devices: "pageDevices",
  storage: "pageStorage",
  pairing: "pagePairing",
};

function $(id) {
  return document.getElementById(id);
}

function t(key, params = {}) {
  const text = (i18n[state.lang] && i18n[state.lang][key]) || i18n.zh[key] || key;
  return text.replace(/\{(\w+)\}/g, (_, name) => params[name] ?? "");
}

function applyTranslations() {
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  $("languageSelect").value = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  $("pageTitle").textContent = t(pageTitleKeys[state.currentTab]);
  $("refreshButton").title = t("refreshNow");
  $("refreshButton").setAttribute("aria-label", t("refreshNow"));
  $("refreshDisksButton").title = t("refreshDisks");
  $("refreshDisksButton").setAttribute("aria-label", t("refreshDisks"));
  $("pairingRefreshButton").title = t("refreshPairing");
  $("pairingRefreshButton").setAttribute("aria-label", t("refreshPairing"));
  if (state.overview) renderOverview(state.overview);
  if (state.audit) renderAuditSummary(state.audit);
  if (state.pairing) renderPairing(state.pairing);
  if (state.updateInfo) renderUpdateBubble(state.updateInfo);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function formatBytes(value) {
  const bytes = Number(value || 0);
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / (1024 ** index)).toFixed(index > 1 ? 1 : 0)} ${units[index]}`;
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return "--";
  if (seconds < 60) return t("durationSeconds", { value: Math.round(seconds) });
  if (seconds < 3600) return t("durationMinutes", { value: Math.floor(seconds / 60) });
  return t("durationHours", {
    hours: Math.floor(seconds / 3600),
    minutes: Math.floor((seconds % 3600) / 60),
  });
}

function formatTime(value) {
  if (!value) return t("noRemoteSeen");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(state.lang === "zh" ? "zh-CN" : "en-US", { hour12: false });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function toast(message, error = false) {
  const node = $("toast");
  node.textContent = message;
  node.classList.toggle("error", error);
  node.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => node.classList.remove("show"), 3200);
}

function restoreButton(button) {
  button.disabled = false;
  if (button.dataset.i18n) {
    button.textContent = t(button.dataset.i18n);
    return;
  }
  if (button.id === "wakeButton") {
    button.innerHTML = `<span aria-hidden="true">⚡</span> <span>${escapeHtml(t("wakeRemote"))}</span>`;
  }
}

function setBusy(button, busy, labelKey) {
  button.disabled = busy;
  if (busy) {
    button.textContent = t(labelKey);
  } else {
    restoreButton(button);
  }
}

function setPowerBadge(node, power) {
  const normalized = ["offline_unknown", "powered_off"].includes(power) ? "offline" : (power || "neutral");
  node.className = `status-badge ${normalized}`;
  node.textContent = t(power || "unknown");
}

function setStateNode(node, power) {
  const normalized = ["offline_unknown", "powered_off"].includes(power) ? "offline" : (power || "");
  node.className = `state-node ${normalized}`;
}

function localizeRemoteDetail(detail) {
  const map = {
    "Companion agent connected": "remoteDetailCompanion",
    "Syncthing connected; companion agent unavailable": "remoteDetailSyncthing",
    "Last power event reported sleep": "remoteDetailSleep",
    "Last power event reported a normal shutdown": "remoteDetailShutdown",
    "Cannot distinguish shutdown, sleep, or network loss without companion heartbeat": "remoteDetailUnknown",
  };
  return t(map[detail] || "remoteDetailUnknown");
}

function syncHealthKey(health) {
  const map = {
    healthy: "healthHealthy",
    syncing: "healthSyncing",
    waiting: "healthWaiting",
    stalled: "healthStalled",
    paused: "healthPaused",
    error: "healthError",
    unavailable: "healthUnavailable",
  };
  return map[health] || "healthUnknown";
}

function syncHealthDetail(sync) {
  const health = sync.health || "unknown";
  const params = { bytes: formatBytes(sync.need_bytes), count: sync.errors || 0 };
  const map = {
    healthy: "healthHealthyDetail",
    syncing: "healthSyncingDetail",
    waiting: "healthWaitingDetail",
    stalled: "healthStalledDetail",
    paused: "healthPausedDetail",
    error: "healthErrorDetail",
    unavailable: "healthUnavailableDetail",
  };
  if (sync.error) return t("syncthingApi", { error: sync.error });
  return t(map[health] || "healthUnknown", params);
}

function healthClass(health) {
  if (["healthy", "syncing"].includes(health)) return "online";
  if (["waiting", "stalled", "paused"].includes(health)) return "warning";
  if (["error", "unavailable"].includes(health)) return "error";
  return "";
}

function renderOverview(data) {
  state.overview = data;
  const config = data.config;
  const sync = data.syncthing;
  const local = data.local;
  const remote = data.remote;
  const remoteAgent = remote.agent || {};
  const completion = Number(sync.completion || 0);

  $("syncPercent").textContent = `${completion.toFixed(1)}%`;
  $("needBytes").textContent = formatBytes(sync.need_bytes);
  $("connectionType").textContent = sync.connected
    ? (sync.is_local ? t("lanDirect") : t("relayWan"))
    : t("disconnected");
  $("folderState").textContent = t(syncHealthKey(sync.health));
  $("syncProgress").style.width = `${Math.max(0, Math.min(100, completion))}%`;
  $("syncHeadline").textContent = `${syncHealthDetail(sync)} · ${sync.connected ? t("connectedAddress", { address: sync.address || "" }) : t("waitingForRemote")}`;

  $("localName").textContent = local.name;
  $("localHost").textContent = local.hostname;
  $("localOs").textContent = local.os;
  $("localIdle").textContent = formatDuration(local.idle_seconds);
  setPowerBadge($("localState"), local.power_state);

  $("remoteName").textContent = config.remote_name;
  $("remoteHost").textContent = remoteAgent.hostname || "Windows";
  $("agentState").textContent = remote.agent_online ? t("companionConnected") : t("companionDisconnected");
  $("remoteLastSeen").textContent = formatTime(remote.last_seen);
  setPowerBadge($("remoteState"), remote.power_state);

  $("deviceLocalTitle").textContent = local.name;
  $("deviceLocalDetail").textContent = `${local.hostname} · ${t(local.power_state || "unknown")}`;
  $("deviceRemoteTitle").textContent = config.remote_name;
  $("deviceRemoteDetail").textContent = localizeRemoteDetail(remote.detail);
  setStateNode($("localStateNode"), local.power_state);
  setStateNode($("remoteStateNode"), remote.power_state);

  $("remoteIp").textContent = config.remote_ip;
  $("remoteMac").textContent = config.remote_mac;
  $("directConnection").textContent = sync.connected ? (sync.address || t("companionConnected")) : t("disconnected");
  $("agentPort").textContent = String(config.remote_agent_port);

  $("liveDot").className = healthClass(sync.health);
  $("liveLabel").textContent = t(syncHealthKey(sync.health));
  $("lastRefresh").textContent = t("updatedAt", {
    time: new Date().toLocaleTimeString(state.lang === "zh" ? "zh-CN" : "en-US", { hour12: false }),
  });

  if (!$("sourcePath").value) {
    $("sourcePath").value = `${config.sync_root}/Motion 1`;
  }
  if (!$("destinationPath").value) {
    $("destinationPath").value = `${config.sync_root}/Motion_1_cross_platform_reviewed`;
  }
  if (!$("projectLocalPath").value) {
    $("projectLocalPath").value = `${config.sync_root}/Projects`;
  }
  if (!$("quickProjectLocalPath").value) {
    $("quickProjectLocalPath").value = $("destinationPath").value || `${config.sync_root}/Projects`;
  }
  if (!$("remoteTargetBase").value) {
    $("remoteTargetBase").value = config.remote_project_base;
  }
  if (!$("quickProjectRemotePath").value) {
    $("quickProjectRemotePath").value = `${config.remote_project_base}\\New_Project`;
  }

  renderJobs(data.jobs || []);
  renderDisks(local.disks || [], remoteAgent.disks || []);
}

function renderJobs(jobs) {
  const list = $("jobList");
  if (!jobs.length) {
    list.innerHTML = `<div class="empty-state">${escapeHtml(t("emptyJobs"))}</div>`;
    return;
  }
  list.innerHTML = jobs.slice(0, 6).map((job) => `
    <div class="job-row">
      <strong title="${escapeHtml(job.destination || job.source || "")}">${escapeHtml(job.message || job.type)}</strong>
      <span>${escapeHtml(job.status)}</span>
      <strong>${Number(job.progress || 0).toFixed(0)}%</strong>
    </div>
  `).join("");
}

function renderDisks(local, remote) {
  renderDiskList($("localDisks"), local, t("noLocalDisks"));
  renderDiskList($("remoteDisks"), remote, t("needsWindowsAgent"));
}

function renderDiskList(container, disks, emptyText) {
  if (!disks || !disks.length) {
    container.innerHTML = `<div class="empty-state">${escapeHtml(emptyText)}</div>`;
    return;
  }
  container.innerHTML = disks.map((disk) => `
    <div class="disk-row">
      <div class="disk-head">
        <strong>${escapeHtml(disk.name || disk.mount)}</strong>
        <span title="${escapeHtml(disk.mount)}">${escapeHtml(disk.mount)}</span>
      </div>
      <div class="disk-bar"><span style="width:${Math.min(100, Number(disk.percent || 0))}%"></span></div>
      <span class="disk-meta">${escapeHtml(t("freeDisk", { free: formatBytes(disk.free), total: formatBytes(disk.total) }))}</span>
    </div>
  `).join("");
}

async function refreshOverview(showError = false) {
  if (state.polling) return;
  state.polling = true;
  try {
    renderOverview(await api("/api/overview"));
  } catch (error) {
    $("liveDot").className = "error";
    $("liveLabel").textContent = t("controlServiceError");
    if (showError) toast(error.message, true);
  } finally {
    state.polling = false;
  }
}

function renderAuditSummary(result) {
  state.audit = result;
  $("auditTotal").textContent = result.total_entries;
  $("auditRenamed").textContent = result.renamed_entries;
  $("auditCollisions").textContent = result.collisions;
  $("auditSkipped").textContent = result.skipped_entries;
  $("reasonChips").innerHTML = Object.entries(result.reason_counts || {})
    .sort((a, b) => b[1] - a[1])
    .map(([reason, count]) => `<span class="reason-chip">${escapeHtml(t(reason))} · ${count}</span>`)
    .join("");
  $("auditExamples").innerHTML = (result.examples || []).map((item) => `
    <tr>
      <td class="mono">${escapeHtml(item.source)}</td>
      <td class="mono">${escapeHtml(item.destination)}</td>
      <td>${item.reasons.map((reason) => escapeHtml(t(reason))).join(state.lang === "zh" ? "、" : ", ")}</td>
    </tr>
  `).join("") || `<tr><td colspan="3">${escapeHtml(t("noRenameNeeded"))}</td></tr>`;
  $("auditSummary").classList.remove("is-hidden");
  $("normalizeButton").disabled = false;
}

async function runAudit(event) {
  event.preventDefault();
  const button = $("auditButton");
  setBusy(button, true, "busyScanning");
  try {
    const result = await api("/api/audit", {
      method: "POST",
      body: JSON.stringify({
        source: $("sourcePath").value.trim(),
        destination: $("destinationPath").value.trim(),
        keep_spaces: $("keepSpaces").checked,
      }),
    });
    renderAuditSummary(result);
    toast(t("auditComplete", { count: result.renamed_entries }));
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function startNormalize() {
  const button = $("normalizeButton");
  if (!state.audit) return;
  setBusy(button, true, "busySubmitted");
  try {
    const result = await api("/api/normalize", {
      method: "POST",
      body: JSON.stringify({
        source: $("sourcePath").value.trim(),
        destination: $("destinationPath").value.trim(),
        keep_spaces: $("keepSpaces").checked,
      }),
    });
    state.activeJob = result.job.id;
    $("normalizeProgress").classList.remove("is-hidden");
    $("normalizeDestination").textContent = result.job.destination;
    await pollActiveJob();
  } catch (error) {
    setBusy(button, false);
    toast(error.message, true);
  }
}

async function pollActiveJob() {
  if (!state.activeJob) return;
  try {
    const job = await api(`/api/jobs/${state.activeJob}`);
    const progress = Number(job.progress || 0);
    $("normalizeStatus").textContent = job.status;
    $("normalizeMessage").textContent = job.error || job.message || "--";
    $("normalizePercent").textContent = `${progress.toFixed(0)}%`;
    $("normalizeProgressBar").style.width = `${Math.max(0, Math.min(100, progress))}%`;
    if (job.status === "completed") {
      state.activeJob = null;
      setBusy($("normalizeButton"), false);
      toast(t("safeCopyDone"));
      await refreshOverview();
      return;
    }
    if (job.status === "failed") {
      state.activeJob = null;
      setBusy($("normalizeButton"), false);
      toast(job.error || t("copyFailed"), true);
      return;
    }
    window.setTimeout(pollActiveJob, 1000);
  } catch (error) {
    window.setTimeout(pollActiveJob, 2000);
  }
}

async function wakeRemote() {
  const button = $("wakeButton");
  setBusy(button, true, "busySending");
  try {
    const result = await api("/api/wake", {
      method: "POST",
      body: JSON.stringify({}),
    });
    toast(t("wakeSent", { targets: result.sent_to.join(", ") }));
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function resumeSync() {
  const button = $("resumeSyncButton");
  setBusy(button, true, "busyResuming");
  try {
    const result = await api("/api/sync/resume", {
      method: "POST",
      body: JSON.stringify({}),
    });
    toast(result.remote_error ? t("resumeLocalOnly") : t("resumeDone"));
    await refreshOverview(true);
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function refreshDisks() {
  const button = $("refreshDisksButton");
  button.disabled = true;
  try {
    const result = await api("/api/disks");
    renderDisks(result.local, result.remote);
    if (result.remote_project_base) $("remoteTargetBase").value = result.remote_project_base;
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function saveTarget(event) {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  setBusy(button, true, "busySaving");
  try {
    await api("/api/remote/target", {
      method: "POST",
      body: JSON.stringify({ path: $("remoteTargetBase").value.trim() }),
    });
    toast(t("targetSaved"));
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function registerProject(event) {
  event.preventDefault();
  const button = $("registerButton");
  setBusy(button, true, "busyRegistering");
  try {
    const result = await registerProjectPayload({
      local_path: $("projectLocalPath").value.trim(),
      folder_id: $("projectFolderId").value.trim(),
      label: $("projectLabel").value.trim(),
      remote_path: $("projectRemotePath").value.trim(),
    });
    toast(t("projectRegistered", { folder: result.folder_id }));
    await refreshOverview();
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function registerProjectPayload(payload) {
  return api("/api/projects/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

async function registerQuickProject(event) {
  event.preventDefault();
  const button = $("quickRegisterButton");
  setBusy(button, true, "busyRegistering");
  try {
    const result = await registerProjectPayload({
      local_path: $("quickProjectLocalPath").value.trim(),
      folder_id: $("quickProjectFolderId").value.trim(),
      label: $("quickProjectLabel").value.trim(),
      remote_path: $("quickProjectRemotePath").value.trim(),
    });
    toast(t("projectRegistered", { folder: result.folder_id }));
    await refreshOverview();
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

function useDestinationForSync() {
  if ($("destinationPath").value.trim()) {
    $("quickProjectLocalPath").value = $("destinationPath").value.trim();
  }
  if (!$("quickProjectLabel").value.trim()) {
    const parts = $("quickProjectLocalPath").value.split(/[\\/]/).filter(Boolean);
    $("quickProjectLabel").value = parts[parts.length - 1] || "";
  }
  toast(t("quickPathCopied"));
}

function renderPairing(data) {
  state.pairing = data;
  const urls = data.controller.dashboard_urls || [];
  $("controllerUrls").innerHTML = urls.length
    ? urls.map((url) => `
      <button class="copy-link" type="button" data-copy="${escapeHtml(url)}">
        <span>${escapeHtml(url)}</span><em>${escapeHtml(t("copyAction"))}</em>
      </button>
    `).join("")
    : `<div class="empty-state">${escapeHtml(t("loading"))}</div>`;
  $("controllerDeviceId").textContent = data.controller.device_id || "--";
  $("pairFolderId").textContent = data.folder.id || "--";
  $("pairFolderPath").textContent = data.folder.path || "--";
  renderKnownDevices(data.known_devices || []);
  renderPendingDevices(data.pending_devices || []);
}

function renderKnownDevices(devices) {
  const container = $("pairKnownDevices");
  const rows = devices.filter((item) => item.device_id);
  if (!rows.length) {
    container.innerHTML = `<div class="empty-state">${escapeHtml(t("noKnownDevices"))}</div>`;
    return;
  }
  container.innerHTML = rows.map((item) => `
    <div class="compact-row">
      <strong>${escapeHtml(item.name || item.device_id)}</strong>
      <span class="mono">${escapeHtml(item.device_id)}</span>
    </div>
  `).join("");
}

function renderPendingDevices(devices) {
  const container = $("pendingDevices");
  if (!devices.length) {
    container.innerHTML = `<div class="empty-state">${escapeHtml(t("nonePending"))}</div>`;
    return;
  }
  container.innerHTML = devices.map((item) => `
    <div class="compact-row action-row">
      <div>
        <strong>${escapeHtml(item.name || item.device_id)}</strong>
        <span class="mono">${escapeHtml(item.device_id)}</span>
      </div>
      <button class="button secondary use-pending" type="button" data-device-id="${escapeHtml(item.device_id)}" data-device-name="${escapeHtml(item.name || "")}">${escapeHtml(t("pendingUse"))}</button>
    </div>
  `).join("");
}

async function refreshPairing(showToast = false) {
  try {
    const result = await api("/api/pairing");
    renderPairing(result);
    if (showToast) toast(t("pairingLoaded"));
  } catch (error) {
    toast(error.message, true);
  }
}

function renderUpdateBubble(info) {
  state.updateInfo = info;
  const node = $("updateBubble");
  if (!info || !info.configured || !info.has_update || localStorage.getItem(`red-lan-sync-dismiss-update-${info.latest_version}`) === "1") {
    node.classList.add("is-hidden");
    return;
  }
  $("updateTitle").textContent = t("updateBubbleTitle", { version: info.latest_version || info.latest_name || "" });
  $("updatePreview").textContent = info.preview || t("updateBubblePreviewFallback");
  $("updateLink").href = info.url || "#";
  node.classList.remove("is-hidden");
}

async function checkUpdates() {
  try {
    renderUpdateBubble(await api("/api/update/check"));
  } catch (error) {
    state.updateInfo = null;
  }
}

function dismissUpdateBubble() {
  if (state.updateInfo?.latest_version) {
    localStorage.setItem(`red-lan-sync-dismiss-update-${state.updateInfo.latest_version}`, "1");
  }
  $("updateBubble").classList.add("is-hidden");
}

async function addDevice(event) {
  event.preventDefault();
  const button = $("addDeviceButton");
  setBusy(button, true, "busyAdding");
  try {
    const result = await api("/api/devices/add", {
      method: "POST",
      body: JSON.stringify({
        name: $("newDeviceName").value.trim(),
        device_id: $("newDeviceId").value.trim(),
        address: $("newDeviceAddress").value.trim() || "dynamic",
      }),
    });
    toast(t("deviceAdded", { name: result.name, folder: result.folder_id }));
    $("newDeviceId").value = "";
    await refreshPairing();
  } catch (error) {
    toast(error.message, true);
  } finally {
    setBusy(button, false);
  }
}

async function copyText(value) {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
  } catch (error) {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
  toast(t("copied"));
}

function setTab(tab) {
  state.currentTab = tab;
  document.querySelectorAll(".nav-tab").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.tab === tab);
  });
  document.querySelectorAll(".tab-panel").forEach((node) => {
    node.classList.toggle("is-active", node.dataset.panel === tab);
  });
  $("pageTitle").textContent = t(pageTitleKeys[tab]);
  if (tab === "storage") refreshDisks();
  if (tab === "pairing") refreshPairing();
}

document.querySelectorAll(".nav-tab").forEach((button) => {
  button.addEventListener("click", () => setTab(button.dataset.tab));
});

$("languageSelect").addEventListener("change", (event) => {
  state.lang = event.target.value;
  localStorage.setItem("red-lan-sync-language", state.lang);
  applyTranslations();
});
$("refreshButton").addEventListener("click", () => refreshOverview(true));
$("refreshDisksButton").addEventListener("click", refreshDisks);
$("pairingRefreshButton").addEventListener("click", () => refreshPairing(true));
$("auditForm").addEventListener("submit", runAudit);
$("normalizeButton").addEventListener("click", startNormalize);
$("wakeButton").addEventListener("click", wakeRemote);
$("resumeSyncButton").addEventListener("click", resumeSync);
$("targetForm").addEventListener("submit", saveTarget);
$("registerForm").addEventListener("submit", registerProject);
$("quickRegisterForm").addEventListener("submit", registerQuickProject);
$("useDestinationForSync").addEventListener("click", useDestinationForSync);
$("addDeviceForm").addEventListener("submit", addDevice);
$("dismissUpdateBubble").addEventListener("click", dismissUpdateBubble);
$("copyDashboardUrl").addEventListener("click", () => copyText((state.pairing?.controller?.dashboard_urls || [])[1] || (state.pairing?.controller?.dashboard_urls || [])[0] || ""));
$("copyControllerId").addEventListener("click", () => copyText(state.pairing?.controller?.device_id || ""));

document.addEventListener("click", (event) => {
  const copyButton = event.target.closest("[data-copy]");
  if (copyButton) {
    copyText(copyButton.dataset.copy);
    return;
  }
  const pendingButton = event.target.closest(".use-pending");
  if (pendingButton) {
    $("newDeviceId").value = pendingButton.dataset.deviceId || "";
    $("newDeviceName").value = pendingButton.dataset.deviceName || $("newDeviceName").value;
  }
});

applyTranslations();
refreshOverview(true);
checkUpdates();
window.setInterval(refreshOverview, 5000);
window.setInterval(checkUpdates, 30 * 60 * 1000);
