# lewis-university-tennis-research
A repository for research, data, and analysis related to Lewis University's undergraduate research.

## Python Package

### Installation

To install the package:

```sh
  git clone
  pip install -e .
  python scripts/init/canonicalize_tennisabstract_data.py
```

To run the Zip extraction, run the following command: `lewis-extract /path/to/zips --raw-destination data/raw`

### File Architecture

- With `src/`, you do once: `pip install -e .`
- Then anywhere: `python3 scripts/init/canonicalize_tennisabstract_data.py`

This makes it so that imports are stable and professional.

```sh
pyproject.toml
src/
  lewis_research/
    __init__.py
    io/
      __init__.py
      paths.py
      dataset_router.py
    pipeline/
      __init__.py
      canonicalize.py
scripts/
  init/
    canonicalize_tennisabstract_data.py
data/
  raw/
  canonical/
  derived/
tests/
README.md
```

### Testing

To test the program, run the following command(s):

```sh
  export PYTHONPATH="$PWD/src"
  python3 test_package.py
```

## Definitions

- **Tabular Data:** Refers to information organized in a structured format of rows and columns, where each row represents a unique record or observation, and each column represents a specific attribute or feature of that record.












### How should we define "forced" or "unforced" errors and will we need to find a definition in an already published paper?

- There is no official rulebook definition of "unforced error" from the ATP, WTA, or ITF.
- The term is not formally defined in the official rules of tennis because it is a statistical and analytical metric.

#### Possible Solutions

- Unforced Error

  - An unforced error is widely understood as a mistake made by a player without significant pressure from the opponent.
    - Meaning they had time, balance, and a reasonable opportunity to make a successful shot but failed due to poor judgment, technique, or execution.

  - [**Unforced Error Definition**](https://www.tennislibrary.com/what-is-an-unforced-error-in-tennis-4657655#unforced-error-definition): In tennis, an unforced error occurs when players make a mistake that is not caused by their opponent’s actions. [**Causes of Unforced Errors**](https://www.tennislibrary.com/what-is-an-unforced-error-in-tennis-4657655#causes-of-unforced-errors): Unforced errors are caused by a player making a mistake or several mistakes during play. 

- Forced Error
  - [**Forced Error Definition**](https://www.tennislibrary.com/what-is-a-forced-error-in-tennis-8854482#forced-error-definition): In tennis, a forced error happens when a player makes a mistake as a direct result of an opponent’s play. [**Causes of Forced Errors**](https://www.tennislibrary.com/what-is-a-forced-error-in-tennis-8854482#causes-of-forced-errors): Most forced errors are caused by your opponent’s skillful play.

- Unforced vs. Forced
  - [**Unforced vs. Forced Errors**](https://www.tennislibrary.com/what-is-a-forced-error-in-tennis-8854482#unforced-vs-forced-errors): While unforced errors are always detrimental, forced errors can be extremely advantageous.
    - Induce a forced error by targeting the opponent's weaker side or by forcing defensive play

### Is this an acceptable unreturnables definition?

- As a general rule, "unreturnables" are points where the returner fails to get a full racquet on the ball (including shanks), get the return all the way to the net, or wildly misses. All other returns are forced or unforced errors.

### Do foot faults only apply to serves and not rally shots?

- Serves vs. Rally Endings

### Do we care that some voulunteers may have guessed or randomly entered values?

- The instructions say, "If for some reason you miss a point or two, that's ok. Entering 'S' in the 1st serve column will give that point to the server; 'R' gives the point to the returner. If you miss several points and are unsure of the sequence go ahead and guess. Add a note in column P to acknowledge the missing information."

### What are point penalties?

- P: Point penalty against server
- Q: Point penalty against returner

### Do we know how challenges or other overrules should be handled or documented?

- According to the instructions, "For now, this system ignores challenges and other overrules. If a point is replayed from the beginning, simply delete the uncounted point and start over. If a challenge affects the result of a point, adjust what you've recorded to reflect the result of the challenge."

- **Exception:**
When a player stops play to challenge or check a mark, there are two possibilities:
  
  - If she is right--that is, she challenges and the ball was out--code the shot as you otherwise would, as a forced or unforced error.
  - However, if she is wrong, use the code `C` to indicate the incorrect decision to stop the rally.
    - `6b29C` means "serve down the T, backhand deep up the middle, play stopped for a challenge [which proved incorrect]."





## Notes

Raw - 710: 20240915-M-Davis_Cup_World_Group-RR-Tallon_Griekspoor-Flavio_Cobolli,Tallon Griekspoor,Flavio Cobolli,R,R,20240915,Davis Cup World Group,RR,18:05,Unipol Arena,Eva Asderaki-Moore,3,1
New - 710: 20240915-M-Davis_Cup_World_Group-RR-Tallon_Griekspoor-Flavio_Cobolli,Tallon Griekspoor,Flavio Cobolli,R,R,20240915,Davis Cup World Group,RR,18:05,Unipol Arena,,Eva Asderaki-Moore,3,1,

Raw - 711: 20240915-M-Davis_Cup_World_Group-RR-Botic_Van_De_Zandschulp-Matteo_Berrettini,R,R,20240915,Davis Cup World Group,RR,15:15,Unipol Arena,Hard,Arnaud Gabas,3,1,Zindaras
New - 711: 20240915-M-Davis_Cup_World_Group-RR-Botic_Van_De_Zandschulp-Matteo_Berrettini,Botic Van De Zandschulp,Matteo Berrettini,R,R,20240915,Davis Cup World Group,RR,15:15,Unipol Arena,Hard,Arnaud Gabas,3,1,Zindaras

Raw - 712: 20240915-M-Davis_Cup_World_Group-RR-Botic_Van_De_Zandschulp-Matteo_Berrettini,Botic Van De Zandschulp,Matteo Berrettini,,,20240915,Davis_Cup_World_Group,RR,,,Hard,,,,Zindaras
New - 712: DELETE

@dataclass
class HttpRequest:
  headers: dict[str, str]
  url: str
  method: str
  data: Union[dict[str, object], bytes]
  timeout: Optional[float] = None
