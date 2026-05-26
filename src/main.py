# The main function, entry to entire program
try:
    # When run as a package: python -m src.main
    from .su_logging import start
except ImportError:
    # When run directly inside src/: python main.py
    from su_logging import start


def main():
    # Run the start program function
    start()


if __name__ == "__main__":
    main()
