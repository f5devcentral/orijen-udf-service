# Orijen-UDF-Service

This tool pulls and runs a container as a service on an instance (ubuntu 20.02/22.04) in F5's [Universal Demo Environment](https://udf.f5.com/info).
The target instance needs ``docker`` and a UDF cloud account (AWS) associated with the deployment. 

## Purpose

The tool kicks off automation that provisions accounts and resources in F5 Distributed Cloud.
UDF is used for authX, scheduling, and virtualized resouces for F5XC labs. 
This tool and associated "orijen" tools ties the XC account lifecycle to the lifecyle of a UDF deployment.

## Usage

The tool runs as a systemd service. There is no user interaction required. 

## Installation

Installers are provided in this repo. 
Run with ``sudo``.

Once you've inspected [the installer](./orijen-udf-install.sh) and the contents of [the container](./app/app.py) you can run the installer directly.

```shell
 sudo curl -s https://raw.githubusercontent.com/f5devcentral/orijen-udf-service/main/orijen-udf-base-install.sh | bash
```

## UDF User Tags Needed

Please see [here](./UserTags.md) for formatting information.

- [X] LabID - Each XC lab has a unique GUID. This is passed into the tool to determine what resources and permissions should be provisioned.
- [X] XC - This is used to identify the instance running the tool ("runner") and/or the CE needing to be registered ("CE").

## Project Orijen

Project [Orijen](https://www.orijenpetfoods.com/) is a collection of tools used by the F5 Sales organization to provide automation and tooling around the F5 Distributed Cloud platform.

## Support

For support, please open a GitHub issue.  Note, the code in this repository is community supported and is not supported by F5 Networks.  For a complete list of supported projects please reference [SUPPORT.md](SUPPORT.md).

## Community Code of Conduct

Please refer to the [F5 DevCentral Community Code of Conduct](code_of_conduct.md).

## License

[Apache License 2.0](LICENSE)

## Copyright

Copyright 2014-2020 F5 Networks Inc.

### F5 Networks Contributor License Agreement

Before you start contributing to any project sponsored by F5 Networks, Inc. (F5) on GitHub, you will need to sign a Contributor License Agreement (CLA).

If you are signing as an individual, we recommend that you talk to your employer (if applicable) before signing the CLA since some employment agreements may have restrictions on your contributions to other projects.
Otherwise by submitting a CLA you represent that you are legally entitled to grant the licenses recited therein.

If your employer has rights to intellectual property that you create, such as your contributions, you represent that you have received permission to make contributions on behalf of that employer, that your employer has waived such rights for your contributions, or that your employer has executed a separate CLA with F5.

If you are signing on behalf of a company, you represent that you are legally entitled to grant the license recited therein.
You represent further that each employee of the entity that submits contributions is authorized to submit such contributions on behalf of the entity pursuant to the CLA.
