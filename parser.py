import pprint

# -------------------------------------------------------------------
# Define our classes for events, groups, and fragments
# -------------------------------------------------------------------

class Message:
    """An event that exchanges data. The exchanged items are stored in a list."""
    def __init__(self, id, exchanged_items):
        self.id = id
        self.exchanged_items = exchanged_items  # a list of exchanged items
        self.type = "message"

    def __repr__(self):
        return f"Message({self.id}, {self.exchanged_items})"


class State:
    """An event that indicates the machine's state."""
    def __init__(self, id, state_info):
        self.id = id
        self.state_info = state_info
        self.type = "state"

    def __repr__(self):
        return f"State({self.id}, {self.state_info})"


class Group:
    """
    Represents one branch (choice) within a fragment.
    A group has a guard condition (optional) and holds a list of events
    (messages or state) as well as nested fragments in chronological order.
    """
    def __init__(self, id, name, guard=None):
        self.id = id
        self.name = name
        self.guard = guard  # The condition required for this group
        self.items = []     # Chronologically ordered events (Message, State) and/or nested fragments
        self.type = "group"

    def add_item(self, item):
        self.items.append(item)

    def __repr__(self):
        guard_str = f", guard={self.guard}" if self.guard is not None else ""
        return f"{self.name}(items={self.items}{guard_str})"


class Fragment:
    """
    Represents a branching point in the scenario.
    A fragment holds one or more groups (each a possible branch/choice).
    """
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.groups = []  # The groups (branches) for this fragment, in the order added
        self.type = "fragment"

    def add_group(self, group):
        self.groups.append(group)

    def __repr__(self):
        return f"{self.name}(groups={self.groups})"


# -------------------------------------------------------------------
# The ScenarioBuilder builds the scenario tree as events occur.
#
# When not inside a fragment, events (messages and state) are added to the base list.
# When inside a fragment, you must first call enter_group(guard=...) to start a branch.
#
# When you call enter_fragment(), the current state is saved so that you can exit
# the fragment later and return to the previous context.
# -------------------------------------------------------------------

class ScenarioBuilder:
    def __init__(self):
        # The base list holds events and fragments in the order they occur.
        self.base = []
        # When inside a fragment these hold the active fragment and group.
        self.current_fragment = None
        self.current_group = None
        # The state_stack saves the (fragment, group) state when entering a new fragment.
        self.state_stack = []
        # Counters for unique IDs.
        self.event_counter = 1
        self.group_counter = 1
        self.fragment_counter = 1

    def add_message(self, exchanged_items):
        """Adds a Message event. If not in a fragment, it goes to the base; otherwise to the current group."""
        message = Message(self.event_counter, exchanged_items)
        self.event_counter += 1

        if self.current_fragment is None:
            self.base.append(message)
            print(f"Added {message} to BASE")
        else:
            if self.current_group is None:
                raise Exception("Error: In a fragment but no group is active. Call enter_group() first.")
            self.current_group.add_item(message)
            print(f"Added {message} to {self.current_group.name} in {self.current_fragment.name}")
        return message

    def add_state(self, state_info):
        """Adds a State event. If not in a fragment, it goes to the base; otherwise to the current group."""
        state_event = State(self.event_counter, state_info)
        self.event_counter += 1

        if self.current_fragment is None:
            self.base.append(state_event)
            print(f"Added {state_event} to BASE")
        else:
            if self.current_group is None:
                raise Exception("Error: In a fragment but no group is active. Call enter_group() first.")
            self.current_group.add_item(state_event)
            print(f"Added {state_event} to {self.current_group.name} in {self.current_fragment.name}")
        return state_event

    def enter_fragment(self):
        """
        Starts a new fragment (branching point).
        The new fragment is attached:
          - Directly to the base if not already in a fragment,
          - Or to the current group's items if nested.
        The current (fragment, group) state is saved.
        """
        frag = Fragment(self.fragment_counter, f"Fragment {self.fragment_counter}")
        self.fragment_counter += 1

        if self.current_fragment is None:
            self.base.append(frag)
        else:
            if self.current_group is None:
                raise Exception("Error: Cannot attach a new fragment because no active group exists.")
            self.current_group.add_item(frag)
        print(f"Entered {frag.name}")

        # Save the current state and update the current fragment.
        self.state_stack.append((self.current_fragment, self.current_group))
        self.current_fragment = frag
        self.current_group = None  # Must call enter_group() next within the fragment.
        return frag

    def enter_group(self, guard=None):
        """
        Starts a new group (branch/choice) within the current fragment.
        Optionally, a guard condition can be provided.
        After calling this, subsequent events will be added to this group.
        """
        if self.current_fragment is None:
            raise Exception("Error: Cannot enter a group when not inside a fragment.")
        group = Group(self.group_counter, f"Group {self.group_counter}", guard=guard)
        self.group_counter += 1
        self.current_fragment.add_group(group)
        self.current_group = group
        guard_text = f" with guard: {guard}" if guard is not None else ""
        print(f"Entered {group.name}{guard_text} in {self.current_fragment.name}")
        return group

    def exit_fragment(self):
        """
        Exits the current fragment and restores the previous (fragment, group) state.
        """
        if not self.state_stack:
            raise Exception("Error: No fragment to exit from.")
        prev_fragment, prev_group = self.state_stack.pop()
        print(f"Exiting {self.current_fragment.name}, returning to " +
              (f"{prev_fragment.name}" if prev_fragment else "BASE"))
        self.current_fragment, self.current_group = prev_fragment, prev_group

    def get_scenario(self):
        """Returns the top-level (base) scenario list."""
        return self.base


# -------------------------------------------------------------------
# A helper function to pretty–print the scenario tree.
# This recursively prints messages, state events, fragments, and groups.
# -------------------------------------------------------------------

def print_scenario(items, indent=0):
    spacer = "  " * indent
    for item in items:
        if isinstance(item, Message) or isinstance(item, State):
            print(f"{spacer}- {item}")
        elif isinstance(item, Fragment):
            print(f"{spacer}- {item.name} (Fragment):")
            for group in item.groups:
                guard_str = f" [Guard: {group.guard}]" if group.guard is not None else ""
                print(f"{spacer}  * {group.name}{guard_str} (Group):")
                print_scenario(group.items, indent + 3)
        else:
            print(f"{spacer}- Unknown item: {item}")


# -------------------------------------------------------------------
# Example usage:
#
# This sample builds a scenario with:
#   - Base-level events (messages and states),
#   - A fragment (branching point) that has two groups with different guard conditions,
#   - And some events within these branches.
# -------------------------------------------------------------------

if __name__ == "__main__":
    builder = ScenarioBuilder()

    # Base-level events:
    builder.add_message(["data1", "data2"])
    builder.add_message(["data3", "data4"])

    # Enter a fragment (branching point)
    builder.enter_fragment()
    # In the fragment, start a branch (group) with a guard condition.
    builder.enter_group(guard="x > 5")
    builder.add_message(["data5"])
    builder.add_state("Processing")

    # Enter a second branch in the same fragment with a different guard.
    builder.enter_group(guard="x <= 5")
    builder.add_message(["data6", "data7"])

    # Exit the fragment to return to the base context.
    builder.exit_fragment()

    # More base-level events:
    builder.add_message(["data8"])

    print("\nFinal Scenario (chronological order):\n")
    print_scenario(builder.get_scenario())

    # Optionally, you can inspect the raw underlying structure:
    print("\nRaw structure (using pprint):")
    pprint.pprint(builder.get_scenario())

    print("\nRaw structure:")
    print(builder.base)
