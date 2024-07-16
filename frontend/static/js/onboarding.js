document.addEventListener('DOMContentLoaded', function () {
    const onboardingContainer = document.getElementById('onboarding-steps');
    const progressBarFill = document.getElementById('progressFill');

    let step = 0;
    let selectedGenres = [];
    let ratings = {};
    let genres = [];
    let movies = [];
    let currentPage = 1;
    const moviesPerPage = 10;
    let totalRatedMovies = 0;
    const totalMoviesToRate = 10;
    const totalSteps = 4;

    async function fetchGenres() {
        try {
            const response = await fetch('/api/v1/genres');
            const data = await response.json();
            genres = data;
            console.log('Fetched genres:', genres);
            renderStep();
        } catch (error) {
            console.error('Error fetching genres:', error);
        }
    }

    async function fetchMovies(page = 1) {
        try {
            const response = await fetch(`/api/v1/movies?page=${page}&per_page=${moviesPerPage}`);
            if (!response.ok) {
                throw new Error(`Server responded with status: ${response.status}`);
            }
            const data = await response.json();
            movies = data.movies;
            renderStep();
        } catch (error) {
            console.error('Error fetching movies:', error);
            onboardingContainer.innerHTML = `<p class="text-red-500">Error loading movies. Please try again later.</p>`;
        }
    }

    async function submitOnboardingData() {
        const userId = localStorage.getItem('userId');  // Retrieve userId from localStorage
        console.log("User ID retrieved from localStorage:", userId);

        if (!userId || isNaN(parseInt(userId))) {
            console.error("Invalid user ID:", userId);
            alert("An error occured: invalid user ID.")
            return;
        }
        const data = {
            id: parseInt(userId),
            genres: selectedGenres,
            ratings: ratings
        };
        console.log("Submitting onboarding data:", data);
        try {
            const response = await fetch('/api/v1/onboarding', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                console.log('Preferences saved successfully');
                window.location.href = '/api/v1/dashboard';
            } else {
                const errorData = await response.json();
                console.error('Failed to save preferences:', errorData);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    function updateProgressBar() {
        const progressPercent = ((step + 1) / totalSteps) * 100;
        progressBarFill.style.width = `${progressPercent}%`;
    }

    function handleGenreToggle(genreId) {
        if (selectedGenres.includes(genreId)) {
            selectedGenres = selectedGenres.filter(id => id !== genreId);
        } else {
            selectedGenres.push(genreId);
        }
    }

    function handleRating(movieId, rating) {
        if (!ratings[movieId]) {
            totalRatedMovies++;
        }
        ratings[movieId] = rating;
    }

    function renderStep() {
        updateProgressBar();
        let content = '';

        switch (step) {
            case 0:
                content = `
                    <div class="w-[350px]">
                        <h2 class="text-2xl font-semibold mb-4">Welcome to CortexEng</h2>
                        <p class="mb-4">Let's personalize your experience. We'll ask you a few questions to tailor our recommendations just for you.</p>
                        <button class="bg-indigo-500 text-white font-bold py-2 px-4 rounded-lg w-full hover:bg-indigo-700 transition duration-300" onclick="window.nextStep()">Get Started</button>
                    </div>
                `;
                break;

            case 1:
                content = `
                <div class="w-[350px]">
                    <h2 class="text-2xl font-semibold mb-4">Select Your Favorite Genres</h2>
                    <p class="mb-4">Choose as many as you like</p>
                    ${genres.map(genre => `
                        <div class="flex items-center space-x-2 mb-2">
                            <input type="checkbox" id="${genre.id}" ${selectedGenres.includes(genre.id) ? 'checked' : ''} onchange="window.handleGenreToggle('${genre.id}')">
                            <label for="${genre.id}">${genre.label || 'Unknown Genre'}</label>
                        </div>
                    `).join('')}
                    <button class="bg-indigo-500 text-white font-bold py-2 px-4 rounded-lg w-full hover:bg-indigo-700 transition duration-300" onclick="window.nextStep()">Next</button>
                </div>
            `;
            break;

        case 2:
            content = `
                <div class="w-[350px]">
                    <h2>Rate These Movies</h2>
                    <p class="mb-4">Help us understand your taste</p>
                    ${movies.map(renderMovieRating).join('')}

                    <div class="flex justify-between mt-4">
                        <button class="bg-indigo-500 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition duration-300" ${currentPage === 1 ? 'disabled' : ''} onclick="window.fetchMovies(${currentPage - 1})">Previous</button>
                        <button class="bg-indigo-500 text-white py-2 px-4 rounded-lg hover:bg-indigo-700 transition duration-300" onclick="window.nextPage()">Next</button>
                    </div>
                </div>
            `;
            break;

            case 3:
                content = `
                    <div class="w-[350px]">
                        <h2 class="text-2xl font-semibold mb-4">All Set!</h2>
                        <p class="mb-4">Thanks for sharing your preferences. We've customized your experience based on your inputs.</p>
                        <button class="bg-indigo-500 text-white font-bold py-2 px-4 rounded-lg w-full hover:bg-indigo-700 transition duration-300" onclick="window.startExploring()">Start Exploring</button>
                    </div>
                `;
                break;
        }

        onboardingContainer.innerHTML = content;
    }

    function renderMovieRating(movie) {
        return `
            <div class="mb-4">
                <p class="font-semibold">${movie.title}</p>
                <div class="flex space-x-1">
                    ${[1, 2, 3, 4, 5].map(star => `
                        <svg onclick="window.handleRating(${movie.id}, ${star})" class="w-6 h-6 cursor-pointer ${ratings[movie.id] >= star ? 'text-yellow-400' : 'text-gray-400'}" fill="${ratings[movie.id] >= star ? 'currentColor' : 'none'}" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
                        </svg>
                    `).join('')}
                </div>
            </div>
        `;
    }

    window.nextStep = function () {
        step++;
        renderStep();
    };

    window.handleGenreToggle = function (genreId) {
        handleGenreToggle(genreId);
        renderStep();
    };

    window.handleRating = function (movieId, rating) {
        handleRating(movieId, rating);
        renderStep();
    };

    window.startExploring = function () {
        // Submit onboarding data before redirecting
        submitOnboardingData();
    };

    window.fetchGenres = fetchGenres;
    window.fetchMovies = fetchMovies;

    window.nextPage = function () {
        if (totalRatedMovies >= totalMoviesToRate) {
            step++;
            renderStep();
        } else {
            currentPage++;
            fetchMovies(currentPage);
        }
    };

    fetchGenres();
    fetchMovies();
});
