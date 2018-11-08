from setuptools import setup

setup(name='jupyter_objc_kernel',
      version='0.1',
      description='Minimalistic Objective C kernel for Jupyter',
      author='Tom Metge',
      author_email='tom@accident-prone.com',
      license='MIT',
      classifiers=[
          'License :: OSI Approved :: MIT License',
      ],
      url='https://github.com/tommetge/jupyter-objc-kernel/',
      download_url='',
      packages=['jupyter_objc_kernel'],
      scripts=['jupyter_objc_kernel/install_objc_kernel'],
      keywords=['jupyter', 'notebook', 'kernel', 'objc'],
      include_package_data=True
      )
