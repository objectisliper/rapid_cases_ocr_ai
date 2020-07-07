"""
Conqueror v.1
System that extracts error messages from screen recordings
of different software error occurrences

Web service startup script

Michael Drozdovsky, 2020
michael@drozdovsky.com
"""
from conqueror.app import app


if __name__ == '__main__':
    app.run(debug=True)
