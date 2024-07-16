module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        'century': ['"Century Gothic"', 'sans-serif'],
      },
      colors: {
        primary: '#00adee',
        secondary: '#262261',
        danger: '#e3342f',
      },
      textColor: theme => theme('colors'),
      height: {
        '96': '24rem',
        '128': '32rem',
        '144': '36rem',

      },
      borderRadius: {
        'xl': '1rem',
        '2xl': '2rem',
        '3xl': '3rem',
        '4xl': '4rem',
        '5xl': '5rem',
      }

    },
  },
  plugins: [],
}

