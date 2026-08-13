// @ts-check
const { themes: prismThemes } = require('prism-react-renderer');

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Agent OS 知识库',
  tagline: '原理 × AWS × IoT — Agent OS 系统工程笔记',
  favicon: 'img/favicon.ico',
  url: 'https://agent-os-gilt.vercel.app',
  baseUrl: '/',
  organizationName: 'agent-os-docs',
  projectName: 'agent-os-docs',
  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',
  i18n: {
    defaultLocale: 'zh-Hans',
    locales: ['zh-Hans'],
  },
  markdown: {
    mermaid: true,
  },
  themes: ['@docusaurus/theme-mermaid'],
  plugins: [
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      {
        hashed: true,
        language: ['zh', 'en'],
        highlightSearchTermsOnTargetPage: true,
        explicitSearchResultPath: true,
      },
    ],
  ],
  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: require.resolve('./sidebars.js'),
          routeBasePath: 'docs',
          showLastUpdateTime: false,
          showLastUpdateAuthor: false,
        },
        blog: false,
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      }),
    ],
  ],
  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      navbar: {
        title: 'Agent OS 知识库',
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'tutorialSidebar',
            position: 'left',
            label: '文档',
          },
          {
            href: 'https://github.com/your-username/agent-os-docs',
            label: 'GitHub',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: '理论基础',
            items: [
              { label: 'CoALA 论文 (2023)', href: 'https://arxiv.org/abs/2309.02427' },
              { label: 'AIOS 论文 (2024)', href: 'https://arxiv.org/abs/2403.16971' },
            ],
          },
          {
            title: 'AWS 文档',
            items: [
              { label: 'Amazon Bedrock AgentCore', href: 'https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html' },
              { label: 'AWS Bedrock 定价', href: 'https://aws.amazon.com/bedrock/pricing/' },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} Agent OS Docs Contributors. Built with Docusaurus.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
        additionalLanguages: ['python', 'bash', 'json', 'yaml'],
      },
      mermaid: {
        theme: { light: 'neutral', dark: 'dark' },
      },
    }),
};

module.exports = config;
