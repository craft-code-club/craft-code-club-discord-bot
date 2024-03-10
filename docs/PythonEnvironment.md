# Python Environment


[<< Back](../README.md)


Working with virtual environments is a good practice to keep your project dependencies isolated from other projects. This way you can have different versions of the same package in different projects.

1. Create a virtual environment
```bash
python -m venv <name_of_the_virtual_environment>

# Example
python -m venv venv
```

2. Activate the virtual environment
```bash
.\<name_of_the_virtual_environment>\Scripts\activate

# Example
.\venv\Scripts\activate
```
In windows using powershell
```powershell
.\<name_of_the_virtual_environment>\Scripts\Activate.ps1

# Example
.\venv\Scripts\Activate.ps1
```

3. Exits the virtual environment
```bash
deactivate
```

4. To remove the virtual environment
```bash
rm -r venv
```
