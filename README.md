PyBitAPI
========

A native API for ByBitmessage


This is a native usable API for using PyBitmessage as a library.

It should be Possible to create a Full-featured GUI using this API.

Licence is under MIT-License, like the original Pybitmessage client.


Usage:

Download Source of PyBitmessage from: 
https://github.com/Bitmessage/PyBitmessage

Put all files from the PyBitAPI/src directory in the PyBitmessage/src directory.

Write your own Program in this directory.

Start it with:

import class_api

api = class_api.getAPI()

Defines the API options
-----------------------
possible values are: 
workingdir='/tmp/testpath'
That is the path, where all pybitmessage files will be created
silent=True
Because PyBitmessage trashes the stdout with a lot of messages,
that's the only way to create a commanline application at the moment
ATTENTION: print could not be used, use sys.stderr.write('text') instead

api.start(daemon=True)

Start PyBitmessage as a backround daemon
----------------------------------------
possible values are:
daemon=False
This will start the original Bitmessage QT-Gui

api.createRandomAddress('testname')

That's an example how the api is used
--------------------------------------
For a list of all api commands have a look at the src/class_api.py

api.stop()

This command should shutdown pybitmessage daemon
------------------------------------------------
sometimes it happens, that long taking operations are still running
in backround, so this stop method doesn't care about real closing.

A Usble Example could be found under:
https://github.com/merlink01/BitShell

Have fun scripting.
