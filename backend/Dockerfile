FROM openkbs/blazegraph:latest

USER root

# the following supplants the existing RWStore.properties file
COPY bg/RWStore.properties /home/developer/blazegraph/conf
COPY bg/log4j.properties /home/developer/blazegraph/conf
COPY bg/run-loader.sh /
COPY bg/pom-blazegraph-loader.xml /

RUN chmod 755 /run-loader.sh && \
    mkdir /blazegraph-data && \
    ln -s /usr/jdk1.8.0_191/bin/java /usr/bin/java

# install the dependencies for the blazegraph loader
RUN mvn package -f /pom-blazegraph-loader.xml

RUN mkdir /biolink-data
WORKDIR /biolink-data
RUN wget https://biolink.github.io/biolink-model/biolink-model.owl
COPY sample.nt /biolink-data

# load the biolink-model.owl file
# NOTE: the format of biolink-model.owl is not recognized by the sesame parsers
# RUN /run-loader.sh -z /home/developer/blazegraph/conf/log4j.properties -g file://biolink -f rdfxml -r assoc -p /home/developer/blazegraph/conf/RWStore.properties -m mvn -l /biolink-data/biolink-model.owl
RUN /run-loader.sh -z /home/developer/blazegraph/conf/log4j.properties -g file://biolink -f ntriples -r assoc -p /home/developer/blazegraph/conf/RWStore.properties -m mvn -l /biolink-data/sample.nt

RUN chown -R developer:developer /blazegraph-data
USER developer
CMD ["java", "-server", "-Xmx10g", "-jar", "-Dbigdata.propertyFile=/home/developer/blazegraph/conf/RWStore.properties", "/home/developer/blazegraph/blazegraph.jar"]