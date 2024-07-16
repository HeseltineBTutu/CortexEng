document.addEventListener("DOMContentLoaded", () => {
  const dashboardData = window.dashboardData;

  const welcomeMessage = document.getElementById("welcomeMessage");
  const preferences = document.getElementById("preferences");
  const recommendations = document.getElementById("recommendations");
  const trendingMovies = document.getElementById("trendingMovies");
  const ratedMovies = document.getElementById("ratedMovies");

  const createMovieCard = (movie) => {
      let genres = 'No genres available';
      if (Array.isArray(movie.genres)) {
          genres = movie.genres.join(', ');
      } else if (typeof movie.genres === 'string') {
          genres = movie.genres;
      }

      const userRating = movie.userRating !== undefined ? movie.userRating : 0;

      return `
          <div class="w-64 h-96 m-2 overflow-hidden transition-all duration-300 transform hover:scale-105 hover:shadow-xl">
              <div class="p-0 h-full flex flex-col">
                  <div class="relative h-3/4">
                      <img src="/api/placeholder/${movie.movieId}/300/450" alt="${movie.title}" class="w-full h-full object-cover" />
                      <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black to-transparent p-4">
                          <h3 class="text-lg font-semibold text-white truncate">${movie.title}</h3>
                          <p class="text-sm text-gray-300 truncate">${genres}</p>
                      </div>
                  </div>
                  <div class="flex items-center justify-between p-4 bg-white dark:bg-gray-800">
                      <div class="flex">
                          ${[...Array(5)].map((_, i) => `
                              <svg class="w-4 h-4 ${i < Math.round(userRating) ? 'text-yellow-400' : 'text-gray-300'}" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                  <polygon points="12 2 15 8.5 22 9.5 17 14.5 18 21.5 12 18 6 21.5 7 14.5 2 9.5 9 8.5 12 2"></polygon>
                              </svg>
                          `).join('')}
                      </div>
                      <span class="text-sm font-semibold">${userRating.toFixed(1)}</span>
                  </div>
              </div>
          </div>
      `;
  };

  const populateDashboard = () => {
      // Populate welcome section
      welcomeMessage.textContent = `Welcome, ${dashboardData.userInfo.firstName}!`;
      preferences.innerHTML = `Your preferences: ${dashboardData.userInfo.preferences.map(pref => `
          <span class="inline-block bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full px-3 py-1 text-sm font-semibold mr-2 mb-2">${pref}</span>
      `).join('')}`;

      // Populate recommendations
      recommendations.innerHTML = dashboardData.recommendations.map(createMovieCard).join('');

      // Populate trending movies
      trendingMovies.innerHTML = dashboardData.trendingMovies.map(createMovieCard).join('');

      // Populate rated movies
      ratedMovies.innerHTML = dashboardData.ratedMovies.map(createMovieCard).join('');
  };

  populateDashboard();

  const toggleDarkMode = () => {
      document.documentElement.classList.toggle('dark');
  };

  document.getElementById("toggleDarkMode").addEventListener("click", toggleDarkMode);
});
