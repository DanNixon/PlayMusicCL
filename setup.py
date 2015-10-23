from setuptools import setup

setup(
    name='playmusiccl',
    version='0.6.2',
    entry_points = {
        'console_scripts': ['playmusiccl=playmusiccl:run'],
    },
    description='Text based command line client for Google Play Music',
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2.7',
        'Topic :: Multimedia :: Sound/Audio :: Players',
    ],
    keywords='google play music command line',
    url='http://github.com/DanNixon/PlayMusicCL',
    author='Dan Nixon',
    author_email='dan@dan-nixon.com',
    license='Apache',
    packages=['playmusiccl'],
    install_requires=[
        'gmusicapi',
        'pylast',
    ],
    include_package_data=True,
    zip_safe=False
)
