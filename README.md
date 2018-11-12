# Minimal Objective-C kernel for Jupyter

## Manual installation

Works only on Linux and OS X. Windows is not supported yet. If you want to use this project on Windows, please use Docker.

Make sure you have the following requirements installed:

 * clang
 * jupyter
 * python 3
 * pip

On Linux, you will need the following (in addition to the above):

 * GNUstep

Most of these dependencies can be installed on Ubuntu (tested on 18.04) with the following:

```bash
sudo apt -y install python3 python3-pip clang
```

You will need to build GNUstep from scratch to use modern Objective C features. The following instructions and a script to automate that process on Ubuntu:

http://wiki.gnustep.org/index.php/GNUstep_under_Ubuntu_Linux

### Kernel Installation:
 * Clone this repo
 * `cd jupyter-objc-kernel`
 * `python3 setup.py install`
 * `install_objc_kernel`
 * `jupyter-notebook`. Enjoy!

## Custom compilation flags

You can use custom compilation flags like so:

![Custom compulation flag](custom_flags.png?raw=true "Example of notebook using custom compilation flags")

Here, the `-lm` flag is passed so you can use the math library.

## Use with Docker

Docker support is pending.

## License

[MIT](LICENSE.txt)
