# Cascading Transitions Experiment

This guide walks you through setting up and running the **Cascading Transitions Experiment**.

---

## 1. Install `uv`

The recommended way to manage environments is using `uv`.

Follow the official installation guide:  
https://docs.astral.sh/uv/getting-started/installation/

---

## 2. Clone the Repository

Create or navigate to your desired project directory, then run:

```bash
git clone https://github.com/van-der-meer/cascades.git
cd cascades
```

Alternatively, you can open the folder directly in VS Code and use the integrated terminal.

---

## 3. Create a Virtual Environment

Create a virtual environment with Python 3.10:

```bash
uv venv --python 3.10
```

---

## 4. Activate the Environment

> You must activate the environment before running the code.  
> You may need to reactivate it when switching sessions.

**Mac / Linux:**
```bash
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

---

## 5. Install Dependencies

Install `psychopy`, `numpy`, and `pyyaml`:

```bash
uv pip install psychopy numpy pyyaml
```

---

## 6. Install `exptools2`

Repository:  

https://github.com/VU-Cog-Sci/exptools2

### Option A: Clone with Git

```bash
git clone https://github.com/VU-Cog-Sci/exptools2.git
```

### Option B: Manual Download

Download the repository and copy the `exptools2` folder into your project directory.

---

## 7. Install `exptools2`

With your virtual environment activated:

```bash
cd exptools2
python setup.py install
```

---

## 8. Troubleshooting

If Python cannot find `exptools2`, try the following workaround:

1. Navigate to:
   ```
   .venv/lib/python3.10/site-packages/exptools2-0.1.dev0-py3.10.egg/exptools2
   ```

2. Copy the `exptools2` folder into:
   ```
   .venv/lib/python3.10/site-packages/
   ```

---

## 9. Verify Installation

If `exptools2` runs without import errors, the setup is successful.

You can now proceed to run the experiment scripts.

---

## 10. Run experiment as specified in the manual


---

## Notes

- Always ensure your virtual environment is activated before running code.
- If something breaks, try reinstalling dependencies inside the environment.
- Keep your environment isolated to avoid version conflicts.

---
