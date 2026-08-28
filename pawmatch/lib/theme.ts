export const colors = {
  background: '#FFF7F3',
  surface: '#FFFFFF',
  surfaceAlt: '#FFF1E8',
  border: '#F0DDD5',
  text: '#1F2A44',
  textMuted: '#6E7585',
  primary: '#FF6F61',
  primarySoft: '#FFE2DD',
  secondary: '#35B8B2',
  secondarySoft: '#DDF6F4',
  accent: '#9C8CF5',
  success: '#38B36C',
  warning: '#FFCC80',
  danger: '#FF5A70',
  shadow: '#D6B6AC',
};

export const spacing = {
  xs: 6,
  sm: 10,
  md: 16,
  lg: 20,
  xl: 24,
  xxl: 32,
};

export const radii = {
  sm: 10,
  md: 16,
  lg: 24,
  xl: 32,
  pill: 999,
};

export const shadows = {
  card: {
    shadowColor: colors.shadow,
    shadowOpacity: 0.14,
    shadowRadius: 18,
    shadowOffset: { width: 0, height: 8 },
    elevation: 4,
  },
  soft: {
    shadowColor: colors.shadow,
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
};
