import attrs
import bs4
import requests


@attrs.define()
class PartySlot:
    filled: bool
    role: str
    job: str = attrs.field(repr=False)

    def __repr__(self) -> str:
        if self.filled:
            return f"<{self.job}>"
        elif self.role == "empty":
            return "<Any>"
        elif self.job == "WHM AST":
            return "<Pure Healer>"
        elif self.job == "SCH SGE":
            return "<Shield Healer>"
        else:
            return f"<{self.role}>"


@attrs.define()
class Listing:
    id: str
    data_centre: str
    category: str
    duty: str
    description: str
    slots: list[PartySlot]
    updated: str
    expires: str

    loot: bool
    duty_complete: bool
    duty_completion: bool
    practice: bool


def scrape() -> list[Listing]:
    listings = []
    req = requests.get("https://xivpf.com/listings")
    req.raise_for_status()
    soup = bs4.BeautifulSoup(req.text, "html.parser")
    for listing in soup.find_all("div", class_="listing"):
        duty = listing.find("div", class_="duty")
        description = listing.find("div", class_="description")
        slots = listing.find_all("div", class_="slot")
        party = []
        for slot in slots:
            role = "tank" if "tank" in slot["class"] else "healer" if "healer" in slot["class"] else "dps" if "dps" in slot["class"] else "empty"
            party.append(
                PartySlot(
                    filled="filled" in slot["class"],
                    role=role,
                    job=slot["title"],
                )
            )
        updated = listing.find("div", class_="updated")
        expires = listing.find("div", class_="expires")
        loot = False
        duty_complete = False
        practice = False
        if "[Loot]" in description.text:
            loot = True
            # description.text.replace('[Loot]', '')
        if "[Duty Complete]" in description.text:
            # description.text.replace('[Duty Complete]', '')
            duty_complete = True
        if "[Duty Completion]" in description.text:
            # description.text.replace('[Duty Completion]', '')
            duty_completion = True
        if "[Practice]" in description.text:
            # description.text.replace('[Practice]', '')
            practice = True

        pf = Listing(
            id=listing["data-id"],
            data_centre=listing["data-centre"],
            category=listing["data-pf-category"],
            duty=duty.text if duty else None,
            description=description.text if description else None,
            slots=party,
            updated=updated.text.strip() if updated else None,
            expires=expires.text.strip() if expires else None,
            loot=loot,
            duty_complete=duty_complete,
            duty_completion=duty_completion,
            practice=practice,
        )

        listings.append(pf)

    return listings


if __name__ == "__main__":
    for listing in scrape():
        if listing.data_centre == "Materia":
            print(listing)
