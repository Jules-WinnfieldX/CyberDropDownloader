FROM python:3.11

WORKDIR /cyberdrop-dl

RUN pip3 install --upgrade cyberdrop-dl

RUN ln -s /cyberdrop-dl/AppData/Configs /cyberdrop-dl/Configs && \
    ln -s /cyberdrop-dl/AppData/Cache /cyberdrop-dl/Cache

ENV APPDATA_FOLDER='/cyberdrop-dl'

CMD /usr/local/bin/python3 /usr/local/bin/cyberdrop-dl --appdata-folder ${APPDATA_FOLDER} --download-all-configs --no-ui
