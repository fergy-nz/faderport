from setuptools import setup

with open('README.md') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    install_requires = f.read()

setup(name='faderport',
      version='1.0.1',
      py_modules=['faderport'],
      package_data={
          '': ['*.txt', '*.md']
      },

      author='jayferg',
      author_email='john@ferguson.net.nz',
      description='An abstract class to interface with a Presonus FaderPort.',
      long_description=long_description,
      long_description_content_type='text/markdown',
      license="MIT",
      python_requires='~=3.6',  # 3.6 and up but not 4.0
      install_requires=install_requires,
      url='https://github.com/jayferg/faderport',
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Intended Audience :: Science/Research',
          'License :: OSI Approved :: MIT License',
          'Operating System :: Microsoft :: Windows',
          'Programming Language :: Python :: 3.6',
          'Topic :: Multimedia :: Sound/Audio :: MIDI',
          'Topic :: Scientific/Engineering :: Human Machine Interfaces',
          'Topic :: Software Development :: User Interfaces',
          'Topic :: System :: Hardware :: Hardware Drivers',
      ]

      )
