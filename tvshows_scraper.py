from lib.builder.tvshows import TvShowsBuilder
from lib.router.entrypoint import main
from lib.router.tvshows import TvShowsRouter
from lib.scraper.tvshows import TvShowsScraper

if __name__ == '__main__':
    main(TvShowsRouter, TvShowsScraper, TvShowsBuilder)
