module.exports = {
  flowFile: 'flows.json',
  credentialSecret: '__NODERED_CREDENTIAL_SECRET__',
  adminAuth: {
    type: 'credentials',
    users: [
      {
        username: '__NODERED_ADMIN_USERNAME__',
        password: '__NODERED_ADMIN_PASSWORD_HASH__',
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
