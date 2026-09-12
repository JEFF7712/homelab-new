module.exports = {
  flowFile: 'flows.json',
  credentialSecret: '${NODERED_CREDENTIAL_SECRET}',
  adminAuth: {
    type: 'credentials',
    users: [
      {
        username: '${NODERED_ADMIN_USERNAME}',
        password: '${NODERED_ADMIN_PASSWORD_HASH}',
        permissions: '*',
      },
    ],
  },
  httpAdminRoot: '/',
  httpNodeRoot: '/',
  httpStatic: [],
  uiPort: 1880,
  uiHost: '0.0.0.0',
  logging: {
    console: {
      level: 'info',
      metrics: false,
      audit: false,
    },
  },
  exportGlobalContextKeys: false,
  externalModules: {
    palette: {
      allowInstall: true,
      allowUpload: false,
    },
    modules: {
      allowInstall: false,
      allowUpload: false,
    },
  },
  editorTheme: {
    projects: { enabled: false },
    codeEditor: { lib: 'monaco' },
  },
  diagnostics: { enabled: true },
  runtimeState: { enabled: false },
};
