import shelve

from sqlitedict import SqliteDict

from chat311.ai_config import AIConfig
from chat311.config import Config
from chat311.main import *


def ask(question: str, session_id: str):
    global ai_name, memory
    # TODO: fill in llm values here
    cfg = Config()
    check_openai_api_key()
    # parse_arguments()
    db = SqliteDict("/tmp/db.sqlite", autocommit=True)
    logger.set_level(logging.DEBUG if cfg.debug_mode else logging.INFO)
    ai_name = "Miami 311 AI representative"
    prompt = AIConfig(
        ai_name=ai_name,
        ai_role="a helpful AI 311 representative for the city of Miami.",
        ai_goals=[
            f"""
Answer the question of a Miami citizen:
            
"{question}"

Please provide a step by step guide or a general answer. Once the answer is obtained, print the answer. Do not ask the user for input.
"""
        ],
    ).construct_full_prompt()
    # print(prompt)
    # Initialize variables
    full_message_history = []
    result = None
    next_action_count = 0
    # Make a constant:
    user_input = "Determine which next command to use, and respond using the format specified above:"
    # Initialize memory and make sure it is empty.
    # this is particularly important for indexing and referencing pinecone memory
    memory = get_memory(cfg, init=True)
    print("Using memory of type: " + memory.__class__.__name__)
    agent = Agent(
        ai_name=ai_name,
        memory=memory,
        full_message_history=full_message_history,
        next_action_count=next_action_count,
        prompt=prompt,
        user_input=user_input,
    )

    # Interaction Loop
    cfg.continuous_limit = 15
    loop_count = 0
    while True:
        # Discontinue if continuous limit is reached
        loop_count += 1
        if (
            cfg.continuous_mode
            and cfg.continuous_limit > 0
            and loop_count > cfg.continuous_limit
        ):
            logger.typewriter_log(
                "Continuous Limit Reached: ",
                Fore.YELLOW,
                f"{cfg.continuous_limit}",
            )
            break

        # Send message to AI, get response
        # with Spinner("Thinking... "):
        assistant_reply = chat311.chat.chat_with_ai(
            agent.prompt,
            agent.user_input,
            agent.full_message_history,
            agent.memory,
            cfg.fast_token_limit,
        )  # TODO: This hardcodes the model to use GPT3.5. Make this an argument

        # Print Assistant thoughts
        print_assistant_thoughts(assistant_reply, ai_name=ai_name)

        # Get command name and arguments
        try:
            command_name, arguments = cmd.get_command(
                attempt_to_fix_json_by_finding_outermost_brackets(
                    assistant_reply
                )
            )
        except Exception as e:
            logger.error("Error: \n", str(e))

        db[session_id] = {
            **db.get(session_id, {}),
            "process": db[session_id]["process"]
            + [{"command": command_name, "arguments": arguments}],
        }

        if not cfg.continuous_mode and agent.next_action_count == 0:
            ### GET USER AUTHORIZATION TO EXECUTE COMMAND ###
            # Get key press: Prompt the user to press enter to continue or escape
            # to exit
            agent.user_input = ""
            logger.typewriter_log(
                "NEXT ACTION: ",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
            )
            print(
                f"Enter 'y' to authorise command, 'y -N' to run N continuous commands, 'n' to exit program, or enter feedback for {agent.ai_name}...",
                flush=True,
            )
            while True:
                console_input = "y"
                # console_input = chat311.utils.clean_input(
                #     Fore.MAGENTA + "Input:" + Style.RESET_ALL
                # )
                if console_input.lower().rstrip() == "y":
                    agent.user_input = "GENERATE NEXT COMMAND JSON"
                    break
                elif console_input.lower().startswith("y -"):
                    try:
                        agent.next_action_count = abs(
                            int(console_input.split(" ")[1])
                        )
                        agent.user_input = "GENERATE NEXT COMMAND JSON"
                    except ValueError:
                        print(
                            "Invalid input format. Please enter 'y -n' where n is the number of continuous tasks."
                        )
                        continue
                    break
                elif console_input.lower() == "n":
                    agent.user_input = "EXIT"
                    break
                else:
                    agent.user_input = console_input
                    command_name = "human_feedback"
                    break

            if agent.user_input == "GENERATE NEXT COMMAND JSON":
                logger.typewriter_log(
                    "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
                    Fore.MAGENTA,
                    "",
                )
            elif agent.user_input == "EXIT":
                print("Exiting...", flush=True)
                break
        else:
            # Print command
            logger.typewriter_log(
                "NEXT ACTION: ",
                Fore.CYAN,
                f"COMMAND = {Fore.CYAN}{command_name}{Style.RESET_ALL}  ARGUMENTS = {Fore.CYAN}{arguments}{Style.RESET_ALL}",
            )

        # Execute command
        if command_name is not None and command_name.lower().startswith(
            "error"
        ):
            result = (
                f"Command {command_name} threw the following error: "
                + arguments
            )
        elif command_name == "human_feedback":
            result = f"Human feedback: {agent.user_input}"
        elif command_name == "print_answer":
            logger.typewriter_log("SYSTEM: ", Fore.YELLOW, str(arguments))
            return {
                "session_id": session_id,
                **arguments,
            }
        else:
            result = f"Command {command_name} returned: {cmd.execute_command(command_name, arguments)}"
            if agent.next_action_count > 0:
                agent.next_action_count -= 1

        memory_to_add = (
            f"Assistant Reply: {assistant_reply} "
            f"\nResult: {result} "
            f"\nHuman Feedback: {agent.user_input} "
        )

        agent.memory.add(memory_to_add)

        # Check if there's a result from the command append it to the message
        # history
        if result is not None:
            agent.full_message_history.append(
                chat311.chat.create_chat_message("system", result)
            )
            logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
        else:
            agent.full_message_history.append(
                chat311.chat.create_chat_message(
                    "system", "Unable to execute command"
                )
            )
            logger.typewriter_log(
                "SYSTEM: ", Fore.YELLOW, "Unable to execute command"
            )
    return {
        "session_id": session_id,
        **arguments,
    }
