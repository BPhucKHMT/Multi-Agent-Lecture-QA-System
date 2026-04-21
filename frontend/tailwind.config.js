/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            color: '#1e293b',
            a: {
              color: '#7c3aed',
              '&:hover': {
                color: '#6d28d9',
              },
            },
            strong: {
              color: '#1e1b4b',
              fontWeight: '700',
            },
            code: {
              color: '#7c3aed',
              backgroundColor: '#f5f3ff',
              padding: '2px 4px',
              borderRadius: '6px',
              fontWeight: '600',
            },
            'code::before': { content: '""' },
            'code::after': { content: '""' },
            ul: {
              listStyleType: 'disc',
              paddingLeft: '1.5rem',
              marginTop: '1.25rem',
              marginBottom: '1.25rem',
            },
            ol: {
              listStyleType: 'decimal',
              paddingLeft: '1.5rem',
              marginTop: '1.25rem',
              marginBottom: '1.25rem',
            },
            li: {
              marginTop: '0.5rem',
              marginBottom: '0.5rem',
            },
            pre: {
              backgroundColor: '#0f172a',
              color: '#f8fafc',
              borderRadius: '12px',
              padding: '1.25rem',
              marginTop: '1.5rem',
              marginBottom: '1.5rem',
              overflowX: 'auto',
              boxShadow: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.05)',
            },
            table: {
              width: '100%',
              marginTop: '1.5rem',
              marginBottom: '1.5rem',
              borderCollapse: 'collapse',
              border: '1px solid #e2e8f0',
              borderRadius: '8px',
              overflow: 'hidden',
            },
            thead: {
              backgroundColor: '#f8fafc',
              borderBottom: '2px solid #e2e8f0',
            },
            'thead th': {
              padding: '0.75rem 1rem',
              textAlign: 'left',
              fontSize: '0.875rem',
              fontWeight: '700',
              color: '#1e293b',
            },
            'tbody td': {
              padding: '0.75rem 1rem',
              borderBottom: '1px solid #f1f5f9',
              fontSize: '0.875rem',
            },
            'tbody tr:last-child td': {
              borderBottom: 'none',
            },
            'tbody tr:nth-child(even)': {
              backgroundColor: '#fcfdff',
            },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
