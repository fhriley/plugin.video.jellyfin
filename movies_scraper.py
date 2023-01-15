from lib.builder.movies import MoviesBuilder
from lib.router.entrypoint import main
from lib.router.movies import MoviesRouter
from lib.scraper.movies import MoviesScraper

if __name__ == '__main__':
    main(MoviesRouter, MoviesScraper, MoviesBuilder)
