
import sys
from . import const
from . import parse_module
from . import parse_table_of_contents
from . import parse_topics
from . import update_module
from . import generate_hierarchy
from . import generate_stub
from . import generate_constants


from . import redirect_output

if len(sys.argv) < 2:
    print(f"""\
Usage:
    {sys.argv[0]} help_sdk_base_dir
""")
    sys.exit(1)

redirect_output(__file__, True)


sdk_base_dir = sys.argv[1]


print(f"\n\nStarting parse_module\n\n")
parse_module.main()


print(f"\n\nStarting parse_table_of_contents\n\n")
parse_table_of_contents.main(sdk_base_dir)

print(f"\n\nStarting parse_topics\n\n")
parse_topics.main(sdk_base_dir)


print(f"\n\nStarting update_module\n\n")
update_module.main()


print(f"\n\nStarting generate_hierarchy\n\n")
generate_hierarchy.main()

print(f"\n\nStarting generate_stub\n\n")
generate_stub.main()

print(f"\n\nStarting generate_constants\n\n")
generate_constants.main()


