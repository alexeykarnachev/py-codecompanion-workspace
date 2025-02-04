# CodeCompanion.nvim Complete Documentation

## Features

- :electric_plug: Support for Anthropic, Copilot, DeepSeek, Gemini, Ollama, OpenAI, Azure OpenAI, HuggingFace and xAI LLMs (or bring your own!)
- :rocket: Inline transformations, code creation and refactoring
- :robot: Variables, Slash Commands, Agents/Tools and Workflows to improve LLM output
- :sparkles: Built in prompt library for common tasks like advice on LSP errors and code explanations
- :building_construction: Create your own custom prompts, Variables and Slash Commands
- :books: Have multiple chats open at the same time
- :muscle: Async execution for fast performance

## Plugin Overview

The plugin uses [adapters](configuration/adapters) to connect to LLMs. Out of the box, the plugin supports:

- Anthropic (`anthropic`) - Requires an API key and supports [prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- Copilot (`copilot`) - Requires a token which is created via `:Copilot setup` in [Copilot.vim](https://github.com/github/copilot.vim)
- DeepSeek (`deepseek`) - Requires an API key
- Gemini (`gemini`) - Requires an API key
- HuggingFace (`huggingface`) - Requires an API key
- Ollama (`ollama`) - Both local and remotely hosted
- OpenAI (`openai`) - Requires an API key
- Azure OpenAI (`azure_openai`) - Requires an Azure OpenAI service with a model deployment
- xAI (`xai`) - Requires an API key

The plugin utilises objects called Strategies. These are the different ways that a user can interact with the plugin. The _chat_ strategy harnesses a buffer to allow direct conversation with the LLM. The _inline_ strategy allows for output from the LLM to be written directly into a pre-existing Neovim buffer.

The plugin allows you to specify adapters for each strategy and also for each [prompt library](configuration/prompt-library) entry.



---

# Configuring CodeCompanion

This section sets out how various elements of CodeCompanion's config can be changed. The examples are shown wrapped in a `require("codecompanion").setup({})` block to work with all plugin managers.

However, if you're using [Lazy.nvim](https://github.com/folke/lazy.nvim), you can apply config changes in the `opts` table which is much cleaner:

```lua
{
  "olimorris/codecompanion.nvim",
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-treesitter/nvim-treesitter",
  },
  opts = {
    strategies = {
      -- Change the default chat adapter
      chat = {
        adapter = "anthropic",
      },
    },
    opts = {
      -- Set debug logging
      log_level = "DEBUG",
    },
  },
},
```
Of course, peruse the rest of this section for more configuration options.


---

# Configuring Adapters

> [!NOTE]
  > The adapters that the plugin supports out of the box can be found [here](https://github.com/olimorris/codecompanion.nvim/tree/main/lua/codecompanion/adapters). It is recommended that you review them so you better understand the settings that can be customized

An adapter is what connects Neovim to an LLM. It's the interface that allows data to be sent, received and processed and there are a multitude of ways to customize them.

## Changing the Default Adapter

You can change the default adapter as follows:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      adapter = "anthropic",
    },
    inline = {
      adapter = "copilot",
    },
  },
}),
```

## Setting an API Key

Extend a base adapter to set options like `api_key` or `model`:

```lua
require("codecompanion").setup({
  adapters = {
    anthropic = function()
      return require("codecompanion.adapters").extend("anthropic", {
        env = {
          api_key = "MY_OTHER_ANTHROPIC_KEY",
        },
      })
    end,
  },
}),
```

If you do not want to store secrets in plain text, prefix commands with `cmd:`:

```lua
require("codecompanion").setup({
  adapters = {
    openai = function()
      return require("codecompanion.adapters").extend("openai", {
        env = {
          api_key = "cmd:op read op://personal/OpenAI/credential --no-newline",
        },
      })
    end,
  },
}),
```

> [!NOTE]
> In this example, we're using the 1Password CLI to extract the OpenAI API Key. You could also use gpg as outlined [here](https://github.com/olimorris/codecompanion.nvim/discussions/601)

## Configuring Adapter Settings

LLMs have many settings such as model, temperature and max_tokens. In an adapter, these sit within a schema table and can be configured during setup:

```lua
require("codecompanion").setup({
  adapters = {
    llama3 = function()
      return require("codecompanion.adapters").extend("ollama", {
        name = "llama3", -- Give this adapter a different name to differentiate it from the default ollama adapter
        schema = {
          model = {
            default = "llama3:latest",
          },
          num_ctx = {
            default = 16384,
          },
          num_predict = {
            default = -1,
          },
        },
      })
    end,
  },
})
```

## Adding a Custom Adapter

> [!NOTE]
> See the [Creating Adapters](/extending/adapters) section to learn how to create custom adapters

Custom adapters can be added to the plugin as follows:

```lua
require("codecompanion").setup({
  adapters = {
    my_custom_adapter = function()
      return {} -- My adapter logic
    end,
  },
}),
```

## Setting a Proxy

A proxy can be configured by utilising the `adapters.opts` table in the config:

```lua
require("codecompanion").setup({
  adapters = {
    opts = {
      allow_insecure = true,
      proxy = "socks5://127.0.0.1:9999",
    },
  },
}),
```

## Changing a Model

Many adapters allow model selection via the `schema.model.default` property:

```lua
require("codecompanion").setup({
  adapters = {
    openai = function()
      return require("codecompanion.adapters").extend("openai", {
        schema = {
          model = {
            default = "gpt-4",
          },
        },
      })
    end,
  },
}),
```

## Example: Using OpenAI Compatible Models

To use any other OpenAI compatible models, change the URL in the env table, set an API key:

```lua
require("codecompanion").setup({
  adapters = {
    ollama = function()
      return require("codecompanion.adapters").extend("openai_compatible", {
        env = {
          url = "http[s]://open_compatible_ai_url", -- optional: default value is ollama url http://127.0.0.1:11434
          api_key = "OpenAI_API_KEY", -- optional: if your endpoint is authenticated
          chat_url = "/v1/chat/completions", -- optional: default value, override if different
        },
      })
    end,
  },
})
```

## Example: Using Ollama Remotely

To use Ollama remotely, change the URL in the env table, set an API key and pass it via an "Authorization" header:

```lua
require("codecompanion").setup({
  adapters = {
    ollama = function()
      return require("codecompanion.adapters").extend("ollama", {
        env = {
          url = "https://my_ollama_url",
          api_key = "OLLAMA_API_KEY",
        },
        headers = {
          ["Content-Type"] = "application/json",
          ["Authorization"] = "Bearer ${api_key}",
        },
        parameters = {
          sync = true,
        },
      })
    end,
  },
})
```

## Example: Azure OpenAI

Below is an example of how you can leverage the `azure_openai` adapter within the plugin:

```lua
require("codecompanion").setup({
  adapters = {
    azure_openai = function()
      return require("codecompanion.adapters").extend("azure_openai", {
        env = {
          api_key = "YOUR_AZURE_OPENAI_API_KEY",
          endpoint = "YOUR_AZURE_OPENAI_ENDPOINT",
        },
        schema = {
          model = {
            default = "YOUR_DEPLOYMENT_NAME",
          },
        },
      })
    end,
  },
  strategies = {
    chat = {
      adapter = "azure_openai",
    },
    inline = {
      adapter = "azure_openai",
    },
  },
}),
```


---

# Configuring the System Prompt

The default system prompt has been carefully curated to deliver terse and professional responses that relate to development and Neovim. It is sent with every request in the chat buffer.

The plugin comes with the following system prompt:

```txt
You are an AI programming assistant named "CodeCompanion". You are currently plugged in to the Neovim text editor on a user's machine.

Your core tasks include:
- Answering general programming questions.
- Explaining how the code in a Neovim buffer works.
- Reviewing the selected code in a Neovim buffer.
- Generating unit tests for the selected code.
- Proposing fixes for problems in the selected code.
- Scaffolding code for a new workspace.
- Finding relevant code to the user's query.
- Proposing fixes for test failures.
- Answering questions about Neovim.
- Running tools.

You must:
- Follow the user's requirements carefully and to the letter.
- Keep your answers short and impersonal, especially if the user responds with context outside of your tasks.
- Minimize other prose.
- Use Markdown formatting in your answers.
- Include the programming language name at the start of the Markdown code blocks.
- Avoid including line numbers in code blocks.
- Avoid wrapping the whole response in triple backticks.
- Only return code that's relevant to the task at hand. You may not need to return all of the code that the user has shared.
- Use actual line breaks instead of '\n' in your response to begin new lines.
- Use '\n' only when you want a literal backslash followed by a character 'n'.
- All non-code responses must be in %s.

When given a task:
1. Think step-by-step and describe your plan for what to build in pseudocode, written out in great detail, unless asked not to do so.
2. Output the code in a single code block, being careful to only return relevant code.
3. You should always generate short suggestions for the next user turns that are relevant to the conversation.
4. You can only give one reply for each conversation turn.
```

## Changing the System Prompt

The default system prompt cant be changed with:

```lua
require("codecompanion").setup({
  opts = {
    system_prompt = function(opts)
      return "My new system prompt"
    end,
  },
}),
```
The `opts` parameter contains the default adapter for the chat strategy (`opts.adapter`) alongside the language (`opts.language`) that the LLM should respond with.


---

# Configuring the Chat Buffer

<p align="center">
  <img src="https://github.com/user-attachments/assets/597299d2-36b3-469e-b69c-4d8fd14838f8" alt="Chat buffer">
</p>

By default, CodeCompanion provides a "chat" strategy that uses a dedicated Neovim buffer for conversational interaction with your chosen LLM. This buffer can be customized according to your preferences.

## Keymaps

You can define or override the default keymaps to send messages, regenerate responses, close the buffer, etc. Example:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      keymaps = {
        send = {
          modes = { n = "<C-s>", i = "<C-s>" },
        },
        close = {
          modes = { n = "<C-c>", i = "<C-c>" },
        },
        -- Add further custom keymaps here
      },
    },
  },
})
```

The keymaps are mapped to `<C-s>` for sending a message and `<C-c>` for closing in both normal and insert modes.

## Variables

Variables are placeholders inserted into the chat buffer (using `#`). They provide contextual code or information about the current Neovim state. For instance, the built-in `#buffer` variable sends the current buffer’s contents to the LLM.

You can even define your own variables to share specific content:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      variables = {
        ["my_var"] = {
          callback = function()
            return "Your custom content here."
          end,
          description = "Explain what my_var does",
          opts = {
            contains_code = false,
          },
        },
      },
    },
  },
})
```

## Slash Commands

Slash Commands (invoked with `/`) let you dynamically insert context into the chat buffer, such as file contents or date/time.

The plugin supports providers like `telescope`, `mini_pick`, `fzf_lua` and `snacks` (as in snacks.nvim). Please see the [Chat Buffer](/usage/chat-buffer/index) usage section for full details:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      slash_commands = {
        ["file"] = {
          callback = "strategies.chat.slash_commands.file",
          description = "Select a file using Telescope",
          opts = {
            provider = "telescope", -- Other options include 'default', 'mini_pick', 'fzf_lua', snacks
            contains_code = true,
          },
        },
      },
    },
  },
})
```

You can also add your own slash commands:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      slash_commands = {
        ["mycmd"] = {
          description = "Describe what mycmd inserts",
          callback = function()
            return "Custom context or data"
          end,
          opts = {
            contains_code = true,
          },
        },
      },
    },
  },
})
```

## Agents and Tools

Tools perform specific tasks (e.g., running shell commands, editing buffers, etc.) when invoked by an LLM. You can group them into an Agent and both can be referenced with `@` when in the chat buffer:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      agents = {
        ["my_agent"] = {
          description = "A custom agent combining tools",
          system_prompt = "Describe what the agent should do",
          tools = {
            "cmd_runner",
            "editor",
            -- Add your own tools or reuse existing ones
          },
        },
      },
      tools = {
        ["my_tool"] = {
          description = "Run a custom task",
          callback = function(command)
            -- Perform the custom task here
            return "Tool result"
          end,
        },
      },
    },
  },
})
```

When users introduce the agent `@my_agent` in the chat buffer, it can call the tools you listed (like `@my_tool`) to perform tasks on your code.

## Layout

You can change the appearance of the chat buffer by changing the `display.chat.window` table in your configuration:

```lua
require("codecompanion").setup({
  display = {
    chat = {
      -- Change the default icons
      icons = {
        pinned_buffer = " ",
        watched_buffer = "👀 ",
      },

      -- Alter the sizing of the debug window
      debug_window = {
        ---@return number|fun(): number
        width = vim.o.columns - 5,
        ---@return number|fun(): number
        height = vim.o.lines - 2,
      },

      -- Options to customize the UI of the chat buffer
      window = {
        layout = "vertical", -- float|vertical|horizontal|buffer
        position = nil, -- left|right|top|bottom (nil will default depending on vim.opt.plitright|vim.opt.splitbelow)
        border = "single",
        height = 0.8,
        width = 0.45,
        relative = "editor",
        opts = {
          breakindent = true,
          cursorcolumn = false,
          cursorline = false,
          foldcolumn = "0",
          linebreak = true,
          list = false,
          numberwidth = 1,
          signcolumn = "no",
          spell = false,
          wrap = true,
        },
      },

      ---Customize how tokens are displayed
      ---@param tokens number
      ---@param adapter CodeCompanion.Adapter
      ---@return string
      token_count = function(tokens, adapter)
        return " (" .. tokens .. " tokens)"
      end,
    },
  },
}),
```

## Diff

> [!NOTE]
> Currently the plugin only supports native Neovim diff or [mini.diff](https://github.com/echasnovski/mini.diff)

If you utilize the `@editor` tool, then the plugin can update a given chat buffer. A diff will be created so you can see the changes made by the LLM.

There are a number of diff settings available to you:

```lua
require("codecompanion").setup({
  display = {
    diff = {
      enabled = true,
      close_chat_at = 240, -- Close an open chat buffer if the total columns of your display are less than...
      layout = "vertical", -- vertical|horizontal split for default provider
      opts = { "internal", "filler", "closeoff", "algorithm:patience", "followwrap", "linematch:120" },
      provider = "default", -- default|mini_diff
    },
  },
}),
```

## UI

### User and LLM Roles

The chat buffer places user and LLM responses under a `H2` header. These can be customized in the configuration:

```lua
require("codecompanion").setup({
  strategies = {
    chat = {
      roles = {
        ---The header name for the LLM's messages
        ---@type string|fun(adapter: CodeCompanion.Adapter): string
        llm = function(adapter)
          return "CodeCompanion (" .. adapter.formatted_name .. ")"
        end,

        ---The header name for your messages
        ---@type string
        user = "Me",
      }
    }
  }
})
```

By default, the LLM's responses will be placed under a header such as `CodeCompanion (DeepSeek)`, leveraging the current adapter in the chat buffer. This option can be in the form of a string or a function that returns a string. If you opt for a function, the first parameter will always be the adapter from the chat buffer.

The user role is currently only available as a string.

### Markdown Rendering

As the Chat Buffer uses markdown as its syntax, you can use popular rendering plugins to improve the UI:

**[render-markdown.nvim](https://github.com/MeanderingProgrammer/render-markdown.nvim)**

```lua
{
  "MeanderingProgrammer/render-markdown.nvim",
  ft = { "markdown", "codecompanion" }
},
```

**[markview.nvim](https://github.com/OXY2DEV/markview.nvim)**

```lua
{
  "OXY2DEV/markview.nvim",
  lazy = false,
  opts = {
    preview = {
      filetypes = { "markdown", "codecompanion" },
      ignore_buftypes = {},
    },
  },
},
```

## Additional Options

There are also a number of other options that you can customize:

```lua
require("codecompanion").setup({
  display = {
    chat = {
      intro_message = "Welcome to CodeCompanion ✨! Press ? for options",
      show_header_separator = false, -- Show header separators in the chat buffer? Set this to false if you're using an external markdown formatting plugin
      separator = "─", -- The separator between the different messages in the chat buffer
      show_references = true, -- Show references (from slash commands and variables) in the chat buffer?
      show_settings = false, -- Show LLM settings at the top of the chat buffer?
      show_token_count = true, -- Show the token count for each response?
      start_in_insert_mode = false, -- Open the chat buffer in insert mode?
    },
  },
}),
```


---

# Configuring the Inline Assistant

<p align="center">
  <img src="https://github.com/user-attachments/assets/21568a7f-aea8-4928-b3d4-f39c6566a23c" alt="Inline Assistant">
</p>

CodeCompanion provides an _inline_ strategy for quick, direct interaction with your code. Unlike the chat buffer, the inline assistant integrates responses directly into the current buffer—allowing the LLM to add or replace code as needed.

## Keymaps

The inline assistant supports keymaps for accepting or rejecting changes:

```lua
require("codecompanion").setup({
  strategies = {
    inline = {
      keymaps = {
        accept_change = {
          modes = { n = "ga" },
          description = "Accept the suggested change",
        },
        reject_change = {
          modes = { n = "gr" },
          description = "Reject the suggested change",
        },
      },
    },
  },
}),
```

In this example, `<leader>a` (or `ga` on some keyboards) accepts inline changes, while `gr` rejects them.

## Layout

If the inline prompt creates a new buffer, you can also customize if this should be output in a vertical/horizontal split or a new buffer:

```lua
require("codecompanion").setup({
  display = {
    inline = {
      layout = "vertical", -- vertical|horizontal|buffer
    },
  }
}),
```

## Diff

Please see the [Diff section](chat-buffer#diff) on the Chat Buffer page for configuration options.


---

# Configuring the Action Palette

<p align="center">
  <img src="https://github.com/user-attachments/assets/0d427d6d-aa5f-405c-ba14-583830251740" alt="Action Palette">
</p>

The Action Palette holds plugin specific items like the ability to launch a chat buffer and the currently open chat buffers alongside displaying the prompts from the [Prompt Library](prompt-library).

## Layout

> [!NOTE]
> The Action Palette also supports [Telescope.nvim](https://github.com/nvim-telescope/telescope.nvim) and [mini.pick](https://github.com/echasnovski/mini.pick)

You can change the appearance of the chat buffer by changing the `display.action_palette` table in your configuration:

```lua
require("codecompanion").setup({
  display = {
    action_palette = {
      width = 95,
      height = 10,
      prompt = "Prompt ", -- Prompt used for interactive LLM calls
      provider = "default", -- default|telescope|mini_pick
      opts = {
        show_default_actions = true, -- Show the default actions in the action palette?
        show_default_prompt_library = true, -- Show the default prompt library in the action palette?
      },
    },
  },
}),
```


---

# Configuring the Prompt Library

The plugin comes with a number of pre-built prompts. As per [the config](https://github.com/olimorris/codecompanion.nvim/blob/main/lua/codecompanion/config.lua), these can be called via keymaps or via the cmdline. These prompts have been carefully curated to mimic those in [GitHub's Copilot Chat](https://docs.github.com/en/copilot/using-github-copilot/asking-github-copilot-questions-in-your-ide). Of course, you can create your own prompts and add them to the Action Palette or even to the slash command completion menu in the chat buffer.

## Adding Prompts

> [!NOTE]
> See the [Creating Prompts](/extending/prompts) guide to learn more on their syntax and how you can create your own

Custom prompts can be added as follows:

```lua
require("codecompanion").setup({
  prompt_library = {
    ["Docusaurus"] = {
      strategy = "chat",
      description = "Write documentation for me",
      opts = {
        index = 11,
        is_slash_cmd = false,
        auto_submit = false,
        short_name = "docs",
      },
      references = {
        {
          type = "file",
          path = {
            "doc/.vitepress/config.mjs",
            "lua/codecompanion/config.lua",
            "README.md",
          },
        },
      },
      prompts = {
        {
          role = "user",
          content = [[I'm rewriting the documentation for my plugin CodeCompanion.nvim, as I'm moving to a vitepress website. Can you help me rewrite it?

I'm sharing my vitepress config file so you have the context of how the documentation website is structured in the `sidebar` section of that file.

I'm also sharing my `config.lua` file which I'm mapping to the `configuration` section of the sidebar.
]],
        },
      },
    },
  },
})
```


---



# Using the Chat Buffer

> [!NOTE]
> The chat buffer has a filetype of `codecompanion` and a buftype of `nofile`

You can open a chat buffer with the `:CodeCompanionChat` command or with `require("codecompanion").chat()`. You can toggle the visibility of the chat buffer with `:CodeCompanionChat Toggle` or `require("codecompanion").toggle()`.

The chat buffer uses markdown as its syntax and `H2` headers separate the user and LLM's responses. The plugin is turn-based, meaning that the user sends a response which is then followed by the LLM's. The user's responses are parsed by [nvim-treesitter](https://github.com/nvim-treesitter/nvim-treesitter) and sent via an adapter to an LLM for a response which is then streamed back into the buffer. A response is sent to the LLM by pressing `<CR>` or `<C-s>`. This can of course be changed as per the [keymaps](#keymaps) section.

## Messages

> [!TIP]
> The message history can be modified via the debug window (`gd`) in the chat buffer

It's important to note that some messages, such as system prompts or context provided via [Slash Commands](/usage/chat-buffer/slash-commands), will be hidden. This is to keep the chat buffer uncluttered from a UI perspective. Using the `gd` keymap opens up the debug window, which allows the user to see the full contents of the messages table which will be sent to the LLM on the next turn.

The message history cannot be altered directly in the chat buffer. However, it can be modified in the debug window. This window is simply a Lua buffer which the user can edit as they wish. To persist any changes, the chat buffer keymaps for sending a message (defaults: `<CR>` or `<C-s>`) can be used.

## Completion

<img src="https://github.com/user-attachments/assets/02b4d5e2-3b40-4044-8a85-ccd6dfa6d271" />

The plugin supports multiple completion plugins out of the box. By default, the plugin will look to setup [blink.cmp](https://github.com/Saghen/blink.cmp) before trying to setup [nvim-cmp](https://github.com/hrsh7th/nvim-cmp). If you don't use a completion plugin, then you can use native completions with no setup, invoking them with `<C-_>` from within the chat buffer.

## Keymaps

The plugin has a host of keymaps available in the chat buffer. Pressing `?` in the chat buffer will conveniently display all of them to you.

The keymaps available to the user in normal mode are:

- `<CR>|<C-s>` to send a message to the LLM
- `<C-c>` to close the chat buffer
- `q` to stop the current request
- `ga` to change the adapter for the currentchat
- `gc` to insert a codeblock in the chat buffer
- `gd` to view/debug the chat buffer's contents
- `gf` to fold any codeblocks in the chat buffer
- `gp` to pin a reference to the chat buffer
- `gw` to watch a referenced buffer
- `gr` to regenerate the last response
- `gs` to toggle the system prompt on/off
- `gx` to clear the chat buffer's contents
- `gy` to yank the last codeblock in the chat buffer
- `[[` to move to the previous header
- `]]` to move to the next header
- `{` to move to the previous chat
- `}` to move to the next chat

## References

<img src="https://github.com/user-attachments/assets/1b44afe1-13f8-4c0f-9199-cb32439eb09e" />

Sharing context with an LLM is crucial in order to generate useful responses. In the plugin, references are defined as output that is shared with a chat buffer via a _Variable_, _Slash Command_ or _Agent/Tool_. They appear in a blockquote entitled `Sharing`. In essence, this is context that you're sharing with an LLM.

> [!IMPORTANT]
> References contain the data of an object at a point in time. By default, they **are not** self-updating

In order to allow for references to self-update, they can be _pinned_ (for files and buffers) or _watched_ (for buffers).

File and buffer references can be _pinned_ to a chat buffer with the `gp` keymap. Pinning results in the content from the object being reloaded and shared with the LLM on every turn. The advantage of this is that the LLM will always receive a fresh copy of the source data regardless of any changes. This can be useful if you're working with agents and tools. However, please note that this can consume a lot of tokens.

Buffer references can be _watched_ via the `gw` keymap. Watching, whilst similar to pinning, is a more token-conscious way of keeping the LLM up to date on the contents of a buffer. Watchers track changes (adds, edits, deletes) in the underlying buffer and update the LLM on each turn, with only those changes.

If a reference is added by mistake, it can be removed from the chat buffer by simply deleting it from the `Sharing` blockquote. On the next turn, all context related to that reference will be removed from the message history.

Finally, it's important to note that all LLM endpoints require the sending of previous messages that make up the conversation. So even though you've shared a reference once, many messages ago, the LLM will always have that context to refer to.

## Settings

<img src="https://github.com/user-attachments/assets/01f1e482-1f7b-474f-ae23-f25cc637f40a" />

When conversing with an LLM, it can be useful to tweak model settings in between responses in order to generate the perfect output. If settings are enabled (`display.chat.show_settings = true`), then a yaml block will be present at the top of the chat buffer which can be modified in between responses. The yaml block is simply a representation of an adapter's schema table.



---

# Using Agents and Tools

> [!TIP]
> More information on how agents and tools work and how you can create your own can be found in the [Creating Tools](/extending/tools.md) guide.

<p align="center">
<img src="https://github.com/user-attachments/assets/f4a5d52a-0de5-422d-a054-f7e97bb76f62" />
</p>

As outlined by Andrew Ng in [Agentic Design Patterns Part 3, Tool Use](https://www.deeplearning.ai/the-batch/agentic-design-patterns-part-3-tool-use), LLMs can act as agents by leveraging external tools. Andrew notes some common examples such as web searching or code execution that have obvious benefits when using LLMs.

In the plugin, tools are simply context and actions that are shared with an LLM via a `system` prompt. The LLM and the chat buffer act as an agent by orchestrating their use within Neovim. Tools give LLM's knowledge and a defined schema which can be included in the response for the plugin to parse, execute and feedback on. Agents and tools can be added as a participant to the chat buffer by using the `@` key.

> [!IMPORTANT]
> The agentic use of some tools in the plugin results in you, the developer, acting as the human-in-the-loop and
> approving their use. I intend on making this easier in the coming releases

## @cmd_runner

The _@cmd_runner_ tool enables an LLM to execute commands on your machine, subject to your authorization. A common example can be asking the LLM to run your test suite and provide feedback on any failures.

## @editor

The _@editor_ tool enables an LLM to modify the code in a Neovim buffer. If a buffer's content has been shared with the LLM then the tool can be used to add, edit or delete specific lines. Consider pinning or watching a buffer to avoid manually re-sending a buffer's content to the LLM.

## @files

The _@files_ tool enables an LLM to perform various file operations on the user's disk, such as:

- Creating a file
- Reading a file
- Reading lines from a file
- Editing a file
- Deleting a file
- Renaming a file
- Copying a file
- Moving a file

> [!NOTE]
> All file operations require approval from the user before they can take place

## @rag

The _@rag_ tool uses [jina.ai](https://jina.ai) to parse a given URL's content and convert it into plain text before sharing with the LLM. It also gives the LLM the ability to search the internet for information.

## @full_stack_dev

The _@full_stack_dev_ agent is a combination of the _@cmd_runner_, _@editor_ and _@files_ tools.



---

# Using Slash Commands

<p>
  <img src="https://github.com/user-attachments/assets/02b4d5e2-3b40-4044-8a85-ccd6dfa6d271" />
</p>

Slash Commands enable you to quickly add context to the chat buffer. They are comprised of values present in the `strategies.chat.slash_commands` table alongside the `prompt_library` table where individual prompts have `opts.is_slash_cmd = true`.

## /buffer

<p>
<img src="https://github.com/user-attachments/assets/1be7593b-f77f-44f9-a418-1d04b3f46785" />
</p>

The _buffer_ slash command enables you to add the contents of any open buffers in Neovim to the chat buffer. The command has native, _Telescope_, _mini.pick_, _fzf.lua_ and _snacks.nvim_ providers available. Also, multiple buffers can be selected and added to the chat buffer as per the video above.

## /fetch

> [!TIP]
> To better understand a Neovim plugin, send its `config.lua` to your LLM via the _fetch_ command alongside a prompt

The _fetch_ slash command allows you to add the contents of a URL to the chat buffer. By default, the plugin uses the awesome and powerful [jina.ai](https://jina.ai) to parse the page's content and convert it into plain text. For convenience, the slash command will cache the output to disk and prompt the user if they wish to restore from the cache, should they look to fetch the same URL.

## /file

The _file_ slash command allows you to add the contents of a file in the current working directory to the chat buffer. The command has native, _Telescope_, _mini.pick_, _fzf.lua_ and _snacks.nvim_ providers available. Also, multiple files can be selected and added to the chat buffer.

## /help

The _help_ slash command allows you to add content from a vim help file (`:h helpfile`), to the chat buffer, by searching for help tags. Currently this is only available for _Telescope_, _mini.pick_, _fzf_lua_ and _snacks.nvim_ providers. By default, the slash command will prompt you to trim a help file that is over 1,000 lines in length.

## /now

The _now_ slash command simply inserts the current datetime stamp into the chat buffer.

## /symbols

> [!NOTE]
> If a filetype isn't supported please consider making a PR to add the corresponding Tree-sitter queries from
> [aerial.nvim](https://github.com/stevearc/aerial.nvim)

The _symbols_ slash command uses Tree-sitter to create a symbolic outline of a file to share with the LLM. This can be a useful way to minimize token consumption whilst sharing the basic outline of a file. The plugin utilizes the amazing work from **aerial.nvim** by using their Tree-sitter symbol queries as the basis. The list of filetypes that the plugin currently supports can be found [here](https://github.com/olimorris/codecompanion.nvim/tree/main/queries).

The command has native, _Telescope_, _mini.pick_, _fzf.lua_ and _snacks.nvim_ providers available. Also, multiple symbols can be selected and added to the chat buffer.

## /terminal

The _terminal_ slash command shares the output from the last terminal buffer with the chat buffer.

## /workspace

The _workspace_ slash command allows users to share defined groups of files and/or symbols with an LLM, alongside some pre-written context. The slash command uses a [codecompanion-workspace.json](https://github.com/olimorris/codecompanion.nvim/blob/main/codecompanion-workspace.json) file, stored in the current working directory, to house this context. It is, in essence, a context management system for your repository.

Whilst LLMs are incredibly powerful, they have no knowledge of the architectural decisions yourself or your team have made on a project. They have no context as to why you've selected the dependencies that you have. And, they can't see how your codebase has evolved over time.

Please see the [Creating Workspaces](/extending/workspace) guide to learn how to build your own.


---

# Using Variables

<p align="center">
  <img src="https://github.com/user-attachments/assets/642ef2df-f1c4-41c4-93e2-baa66d7f0801" />
</p>

Variables allow you to share data about the current state of Neovim with an LLM. Simply type `#` in the chat buffer and trigger code completion if you're not using blink.cmp or nvim-cmp. Alternatively, type the variables manually. After the response is sent to the LLM, you should see the variable output tagged as a reference in the chat buffer.

Custom variables can be shared by adding them to the `strategies.chat.variables` table in your configuration.

## #buffer

The _#buffer_ variable shares the full contents from the buffer that the user was last in when they initiated `:CodeCompanionChat`. To select another buffer, use the _/buffer_ slash command. These buffers can be [pinned or watched](/usage/chat-buffer/index#references) to enable updated content to be automatically shared with the LLM.

## #lsp

> [!TIP]
> The [Action Palette](/usage/action-palette) has a pre-built prompt which asks an LLM to explain LSP diagnostics in a
> visual selection

The _#lsp_ variable shares any information from the LSP servers that active in the current buffer. This can serve as useful context should you wish to troubleshoot any errors with an LLM.

## #viewport

The _#viewport_ variable shares with the LLM, exactly what you see on your screen at the point a response is sent (excluding the chat buffer of course).



---

# Using the Inline Assistant

<p align="center">
  <img src="https://github.com/user-attachments/assets/21568a7f-aea8-4928-b3d4-f39c6566a23c" />
</p>

As per the [Getting Started](/getting-started.md#inline-assistant) guide, the Inline Assistant enables you to code directly into a Neovim buffer. Simply run `:CodeCompanion <your prompt>`.

The Assistant has knowledge of your last conversation from a chat buffer. A prompt such as `:CodeCompanion add the new function here` will see the Assistant add a code block directly into the current buffer.

> [!TIP]
> To ensure the LLM has enough context the complete your request, it's recommended to use the `/buffer` prompt

For convenience, you can call prompts from the [prompt library](/configuration/prompt-library) via the Assistant such as `:'<,'>CodeCompanion /buffer what does this file do?`.

## Classification

One of the challenges with inline editing is determining how the LLM's response should be handled in the buffer. If you've prompted the LLM to _"create a table of 5 common text editors"_ then you may wish for the response to be placed at the cursor's position in the current buffer. However, if you asked the LLM to _"refactor this function"_ then you'd expect the response to _replace_ a visual selection. The plugin uses the inline LLM you've specified in your config to determine if the response should:

- _replace_ - replace a visual selection you've made
- _add_ - be added in the current buffer at the cursor position
- _before_ to be added in the current buffer before the cursor position
- _new_ - be placed in a new buffer
- _chat_ - be placed in a chat buffer

## Diff Mode

By default, an inline assistant prompt will trigger the diff feature, showing differences between the original buffer and the changes from the LLM. This can be turned off in your config via the `display.diff.provider` table. You can also choose to accept or reject the LLM's suggestions with the following keymaps:

- `ga` - Accept an inline edit
- `gr` - Reject an inline edit

These keymaps can also be changed in your config via the `strategies.inline.keymaps` table.



---

# Using Workflows

To be updated.


---

# Events / Hooks

In order to enable a tighter integration between CodeCompanion and your Neovim config, the plugin fires events at various points during its lifecycle.

## List of Events

The events that you can access are:

- `CodeCompanionChatCreated` - Fired after a chat has been created for the first time
- `CodeCompanionChatOpened` - Fired after a chat has been opened
- `CodeCompanionChatHidden` - Fired after a chat has been hidden
- `CodeCompanionChatClosed` - Fired after a chat has been permanently closed
- `CodeCompanionChatAdapter` - Fired after the adapter has been set in the chat
- `CodeCompanionChatModel` - Fired after the model has been set in the chat
- `CodeCompanionChatPin` - Fired after a pinned reference has been updated in the messages table
- `CodeCompanionToolAdded` - Fired when a tool has been added to a chat
- `CodeCompanionAgentStarted` - Fired when an agent has been initiated in the chat
- `CodeCompanionAgentFinished` - Fired when an agent has finished all tool executions
- `CodeCompanionInlineStarted` - Fired at the start of the Inline strategy
- `CodeCompanionInlineFinished` - Fired at the end of the Inline strategy
- `CodeCompanionRequestStarted` - Fired at the start of any API request
- `CodeCompanionRequestFinished` - Fired at the end of any API request
- `CodeCompanionDiffAttached` - Fired when in Diff mode
- `CodeCompanionDiffDetached` - Fired when exiting Diff mode

## Event Data

Each event also comes with a data payload. For example, with `CodeCompanionRequestStarted`:

```lua
{
  buf = 10,
  data = {
    adapter = {
      formatted_name = "Copilot",
      model = "o3-mini-2025-01-31",
      name = "copilot"
    },
    bufnr = 10,
    id = 6107753,
    strategy = "chat"
  },
  event = "User",
  file = "CodeCompanionRequestStarted",
  group = 14,
  id = 30,
  match = "CodeCompanionRequestStarted"
}
```

And the `CodeCompanionRequestFinished` also has a `data.status` value.

## Consuming an Event

Events can be hooked into as follows:

```lua
local group = vim.api.nvim_create_augroup("CodeCompanionHooks", {})

vim.api.nvim_create_autocmd({ "User" }, {
  pattern = "CodeCompanionInline*",
  group = group,
  callback = function(request)
    if request.match == "CodeCompanionInlineFinished" then
      -- Format the buffer after the inline request has completed
      require("conform").format({ bufnr = request.buf })
    end
  end,
})
```



---

# User Interface

CodeCompanion aims to keep any changes to the user's UI to a minimum. Aesthetics, especially in Neovim, are highly subjective. So whilst it won't set much by default, it does endeavour to allow users to hook into the plugin and customize the UI to their liking via [Events](events).

Below are some examples of how you can customize the UI related to CodeCompanion.

## [Fidget.nvim](https://github.com/j-hui/fidget.nvim) progress by [@jessevdp](https://github.com/jessevdp)

<p align="center">
<video controls muted src="https://github.com/user-attachments/assets/f1419889-7b62-46f2-ba73-98327a1b378b"></video>
</p>

As per the [discussions](https://github.com/olimorris/codecompanion.nvim/discussions/813):

```lua
-- lua/plugins/codecompanion.lua

return {
  {
    "olimorris/codecompanion.nvim",
    dependencies = {
      -- ...
      "j-hui/fidget.nvim"
    },
    opts = {
      strategies = {
        -- ...
      },
    },
    init = function()
      require("plugins.codecompanion.fidget-spinner"):init()
    end,
  },
}
```

```lua
-- lua/plugins/codecompanion/fidget-spinner.lua

local progress = require("fidget.progress")

local M = {}

function M:init()
  local group = vim.api.nvim_create_augroup("CodeCompanionFidgetHooks", {})

  vim.api.nvim_create_autocmd({ "User" }, {
    pattern = "CodeCompanionRequestStarted",
    group = group,
    callback = function(request)
      local handle = M:create_progress_handle(request)
      M:store_progress_handle(request.data.id, handle)
    end,
  })

  vim.api.nvim_create_autocmd({ "User" }, {
    pattern = "CodeCompanionRequestFinished",
    group = group,
    callback = function(request)
      local handle = M:pop_progress_handle(request.data.id)
      if handle then
        M:report_exit_status(handle, request)
        handle:finish()
      end
    end,
  })
end

M.handles = {}

function M:store_progress_handle(id, handle)
  M.handles[id] = handle
end

function M:pop_progress_handle(id)
  local handle = M.handles[id]
  M.handles[id] = nil
  return handle
end

function M:create_progress_handle(request)
  return progress.handle.create({
    title = " Requesting assistance (" .. request.data.strategy .. ")",
    message = "In progress...",
    lsp_client = {
      name = M:llm_role_title(request.data.adapter),
    },
  })
end

function M:llm_role_title(adapter)
  local parts = {}
  table.insert(parts, adapter.formatted_name)
  if adapter.model and adapter.model ~= "" then
    table.insert(parts, "(" .. adapter.model .. ")")
  end
  return table.concat(parts, " ")
end

function M:report_exit_status(handle, request)
  if request.data.status == "success" then
    handle.message = "Completed"
  elseif request.data.status == "error" then
    handle.message = " Error"
  else
    handle.message = "󰜺 Cancelled"
  end
end

return M
```

## [Lualine.nvim](https://github.com/nvim-lualine/lualine.nvim) integration

The plugin can be integrated with lualine.nvim to show an icon in the statusline when a request is being sent to an LLM:

```lua
local M = require("lualine.component"):extend()

M.processing = false
M.spinner_index = 1

local spinner_symbols = {
  "⠋",
  "⠙",
  "⠹",
  "⠸",
  "⠼",
  "⠴",
  "⠦",
  "⠧",
  "⠇",
  "⠏",
}
local spinner_symbols_len = 10

-- Initializer
function M:init(options)
  M.super.init(self, options)

  local group = vim.api.nvim_create_augroup("CodeCompanionHooks", {})

  vim.api.nvim_create_autocmd({ "User" }, {
    pattern = "CodeCompanionRequest*",
    group = group,
    callback = function(request)
      if request.match == "CodeCompanionRequestStarted" then
        self.processing = true
      elseif request.match == "CodeCompanionRequestFinished" then
        self.processing = false
      end
    end,
  })
end

-- Function that runs every time statusline is updated
function M:update_status()
  if self.processing then
    self.spinner_index = (self.spinner_index % spinner_symbols_len) + 1
    return spinner_symbols[self.spinner_index]
  else
    return nil
  end
end

return M
```

## [Heirline.nvim](https://github.com/rebelot/heirline.nvim) integration

The plugin can also be integrated into heirline.nvim to show an icon when a request is being sent to an LLM:

```lua
local CodeCompanion = {
  static = {
    processing = false,
  },
  update = {
    "User",
    pattern = "CodeCompanionRequest*",
    callback = function(self, args)
      if args.match == "CodeCompanionRequestStarted" then
        self.processing = true
      elseif args.match == "CodeCompanionRequestFinished" then
        self.processing = false
      end
      vim.cmd("redrawstatus")
    end,
  },
  {
    condition = function(self)
      return self.processing
    end,
    provider = " ",
    hl = { fg = "yellow" },
  },
}
```



---

# Creating Adapters

In CodeCompanion, adapters are interfaces that act as a bridge between the plugin's functionality and an LLM. All adapters must follow the interface, below.

This guide is intended to serve as a reference for anyone who wishes to contribute an adapter to the plugin or understand the inner workings of existing adapters.

## The Interface

Let's take a look at the interface of an adapter as per the `adapter.lua` file:

```lua
---@class CodeCompanion.Adapter
---@field name string The name of the adapter e.g. "openai"
---@field formatted_name string The formatted name of the adapter e.g. "OpenAI"
---@field roles table The mapping of roles in the config to the LLM's defined roles
---@field url string The URL of the LLM to connect to
---@field env? table Environment variables which can be referenced in the parameters
---@field env_replaced? table Replacement of environment variables with their actual values
---@field headers table The headers to pass to the request
---@field parameters table The parameters to pass to the request
---@field raw? table Any additional curl arguments to pass to the request
---@field opts? table Additional options for the adapter
---@field handlers table Functions which link the output from the request to CodeCompanion
---@field handlers.setup? fun()
---@field handlers.form_parameters fun()
---@field handlers.form_messages fun()
---@field handlers.chat_output fun()
---@field handlers.inline_output fun()
---@field handlers.on_exit? fun()
---@field handlers.teardown? fun()
---@field schema table Set of parameters for the LLM that the user can customise in the chat buffer
```

Everything up to the handlers should be self-explanatory. We're simply providing details of the LLM's API to the curl library and executing the request. The real intelligence of the adapter comes from the handlers table which is a set of functions which bridge the functionality of the plugin to the LLM.

## Environment Variables

When building an adapter, you'll need to inject variables into different parts of the adapter class. If we take the [Google Gemini](https://github.com/google-gemini/cookbook/blob/main/quickstarts/rest/Streaming_REST.ipynb) endpoint as an example, we need to inject the model and API key variables into the URL of `https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse&key=${api_key}`. Whereas with [OpenAI](https://platform.openai.com/docs/api-reference/authentication), we need an `Authorization` http header to contain our API key.

Let's take a look at the `env` table from the Google Gemini adapter that comes with the plugin:

```lua
url = "https://generativelanguage.googleapis.com/v1beta/models/${model}:streamGenerateContent?alt=sse&key=${api_key}",
env = {
  api_key = "GEMINI_API_KEY",
  model = "schema.model.default",
},
```

The key `api_key` represents the name of the variable which can be injected in the adapter, and the value can represent one of:

- A command to execute on the user's system
- An environment variable from the user's system
- A function to be executed at runtime
- A path to an item in the adapter's schema table
- A plain text value

> [!NOTE]
> Environment variables can be injected into the `url`, `headers` and `parameters` fields of the adapter class at runtime

**Commands**

An environment variable can be obtained from running a command on a user's system. This can be accomplished by prefixing the value with `cmd:` such as:

```lua
env = {
  api_key = "cmd:op read op://personal/Gemini_API/credential --no-newline",
},
```

In this example, we're running the `op read` command to get a credential from 1Password.

**Environment Variable**

An environment variable can also be obtained by using lua's `os.getenv` function. Simply enter the name of the variable as a string such as:

```lua
env = {
  api_key = "GEMINI_API_KEY",
},
```

**Functions**

An environment variable can also be resolved via the use of a function such as:

```lua
env = {
  api_key = function()
    return os.getenv("GEMINI_API_KEY")
  end,
},
```

**Schema Values**

An environment variable can also be resolved by entering the path to a value in a table on the adapter class. For example:

```lua
env = {
  model = "schema.model.default",
},
```

In this example, we're getting the value of a user's chosen model from the schema table on the adapter.

## Handlers

Currently, the handlers table requires four functions to be implemented:

- `form_parameters` - A function which can be used to set the parameters of the request
- `form_messages` - _Most_ LLMs have a `messages` array in the body of the request which contains the conversation. This function can be used to format and structure that array
- `chat_output` - A function to format the output of the request into a Lua table that plugin can parse for the chat buffer
- `inline_output` - A function to format the output of the request into a Lua table that plugin can parse, inline, to the current buffer

There are some optional handlers which you can make use of:

- `on_exit` - A function which receives the full payload from the API and is run once the request completes. Useful for
  handling errors
- `tokens` - A function to determine the amount of tokens consumed in the request(s)
- `setup` - The function which is called before anything else
- `teardown` - A function which is called last and after the request has completed

Let's take a look at a real world example of how we've implemented the OpenAI adapter.

> [!TIP]
> All of the adapters in the plugin come with their own tests. These serve as a great reference to understand how they're working with the output of the API

### OpenAI's API Output

If we reference the OpenAI [documentation](https://platform.openai.com/docs/guides/text-generation/chat-completions-api) we can see that they require the messages to be in an array which consists of `role` and `content`:

```sh
curl https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-4-0125-preview",
    "messages": [
      {
        "role": "user",
        "content": "Explain Ruby in two words"
      }
    ]
  }'
```

### Chat Buffer Output

The chat buffer, which is structured like:

```markdown
## Me

Explain Ruby in two words
```

results in the following output:

```lua
{
  {
    role = "user",
    content = "Explain Ruby in two words"
  }
}
```

### `form_messages`

The chat buffer's output is passed to this handler in for the form of the `messages` parameter. So we can just output this as part of a messages table:

```lua
handlers = {
  form_messages = function(self, messages)
    return { messages = messages }
  end,
}
```

### `chat_output`

Now let's look at how we format the output from OpenAI. Running that request results in:

```txt
data: {"id":"chatcmpl-90DdmqMKOKpqFemxX0OhTVdH042gu","object":"chat.completion.chunk","created":1709839462,"model":"gpt-4-0125-preview","system_fingerprint":"fp_70b2088885","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}]}
```

```txt
data: {"id":"chatcmpl-90DdmqMKOKpqFemxX0OhTVdH042gu","object":"chat.completion.chunk","created":1709839462,"model":"gpt-4-0125-preview","system_fingerprint":"fp_70b2088885","choices":[{"index":0,"delta":{"content":"Programming"},"logprobs":null,"finish_reason":null}]}
```

```txt
data: {"id":"chatcmpl-90DdmqMKOKpqFemxX0OhTVdH042gu","object":"chat.completion.chunk","created":1709839462,"model":"gpt-4-0125-preview","system_fingerprint":"fp_70b2088885","choices":[{"index":0,"delta":{"content":" language"},"logprobs":null,"finish_reason":null}]},
```

```txt
data: [DONE]
```

> [!IMPORTANT]
> Note that the `chat_output` handler requires a table containing `status` and `output` to be returned.

Remember that we're streaming from the API so the request comes through in batches. Thankfully the `http.lua` file handles this and we just have to handle formatting the output into the chat buffer.

The first thing to note with streaming endpoints is that they don't return valid JSON. In this case, the output is prefixed with `data: `. CodeCompanion comes with some handy utility functions to work with this:

```lua
-- Put this at the top of your adapter
local utils = require("codecompanion.utils.adapters")

handlers = {
  chat_output = function(self, data)
    data = utils.clean_streamed_data(data)
  end
}
```

> [!IMPORTANT]
> The data passed to the `chat_output` handler is the response from OpenAI

We can then decode the JSON using native vim functions:

```lua
handlers = {
  chat_output = function(self, data)
    data = utils.clean_streamed_data(data)
    local ok, json = pcall(vim.json.decode, data, { luanil = { object = true } })
  end
}
```

We want to include any nil values so we pass in `luanil = { object = true }`.

Examining the output of the API, we see that the streamed data is stored in a `choices[1].delta` table. That's easy to pickup:

```lua
handlers = {
  chat_output = function(self, data)
    ---
    local delta = json.choices[1].delta
  end
}
```

and we can then access the new streamed data that we want to write into the chat buffer, with:

```lua
handlers = {
  chat_output = function(self, data)
    local output = {}
    ---
    local delta = json.choices[1].delta

    if delta.content then
      output.content = delta.content
      output.role = delta.role or nil
    end
  end
}
```

And then we can return the output in the following format:

```lua
handlers = {
  chat_output = function(self, data)
    --
    return {
      status = "success",
      output = output,
    }
  end
}
```

Now if we put it all together, and put some checks in place to make sure that we have data in our response:

```lua
handlers = {
  chat_output = function(self, data)
    local output = {}

    if data and data ~= "" then
      data = utils.clean_streamed_data(data)
      local ok, json = pcall(vim.json.decode, data, { luanil = { object = true } })

      local delta = json.choices[1].delta

      if delta.content then
        output.content = delta.content
        output.role = delta.role or nil

        return {
          status = "success",
          output = output,
        }
      end
    end
  end
},
```

### `form_parameters`

For the purposes of the OpenAI adapter, no additional parameters need to be created. So we just pass this through:

```lua
handlers = {
  form_parameters = function(self, params, messages)
    return params
  end,
}
```

### `inline_output`

From a design perspective, the inline strategy is very similar to the chat strategy. With the `inline_output` handler we simply return the content we wish to be streamed into the buffer.

In the case of OpenAI, once we've checked the data we have back from the LLM and parsed it as JSON, we simply need to:

```lua
---Output the data from the API ready for inlining into the current buffer
---@param self CodeCompanion.Adapter
---@param data table The streamed JSON data from the API, also formatted by the format_data handler
---@param context table Useful context about the buffer to inline to
---@return string|table|nil
inline_output = function(self, data, context)
  -- Data cleansed, parsed and validated
  -- ..
  local content = json.choices[1].delta.content
  if content then
    return content
  end
end,
```

The `inline_output` handler also receives context from the buffer that initiated the request.

### `on_exit`

Handling errors from a streaming endpoint can be challenging. It's recommended that any errors are managed in the `on_exit` handler which is initiated when the response has completed. In the case of OpenAI, if there is an error, we'll see a response back from the API like:

```sh
data: {
data:     "error": {
data:         "message": "Incorrect API key provided: 1sk-F18b****************************************XdwS. You can find your API key at https://platform.openai.com/account/api-keys.",
data:         "type": "invalid_request_error",
data:         "param": null,
data:         "code": "invalid_api_key"
data:     }
data: }
```

This would be challenging to parse! Thankfully we can leverage the `on_exit` handler which receives the final payload, resembling:

```lua
{
  body = '{\n    "error": {\n        "message": "Incorrect API key provided: 1sk-F18b****************************************XdwS. You can find your API key at https://platform.openai.com/account/api-keys.",\n        "type": "invalid_request_error",\n        "param": null,\n        "code": "invalid_api_key"\n    }\n}',
  exit = 0,
  headers = { "date: Thu, 03 Oct 2024 08:05:32 GMT" },
  status = 401
}
```

and that's much easier to work with:

```lua
---Function to run when the request has completed. Useful to catch errors
---@param self CodeCompanion.Adapter
---@param data table
---@return nil
on_exit = function(self, data)
  if data.status >= 400 then
    log:error("Error: %s", data.body)
  end
end,
```

The `log:error` call ensures that any errors are logged to the logfile as well as displayed to the user in Neovim. It's also important to reference that the `chat_output` and `inline_output` handlers need to be able to ignore any errors from the API and let `on_exit` handle them.

### `setup` and `teardown`

There are two optional handlers that you can make use of: `setup` and `teardown`.

The `setup` handler will execute before the request is sent to the LLM's endpoint and before the environment variables have been set. This is leveraged in the Copilot adapter to obtain the token before it's resolved as part of the environment variables table. The `setup` handler **must** return a boolean value so the `http.lua` file can determine whether to proceed with the request.

The `teardown` handler will execute once the request has completed and after `on_exit`.

### The Utility File

A lot of LLM endpoints claim to be "OpenAI Compatible" yet have odd quirks which prevent you from using the OpenAI Adapter. Common issues can be:

- System messages have to be the first message (`anthropic`, `deepseek`)
- System messages have to be one message (`anthropic`, `deepseek`)
- Messages must follow a `User -> LLM -> User -> LLM` turn based flow (`deepseek`)

To address this, an [adapter utilities](https://github.com/olimorris/codecompanion.nvim/blob/main/lua/codecompanion/utils/adapters.lua) file has been created that you can leverage in building or extending your own adapters. Finally, always refer to the pre-built adapters as a reference point.

## Schema

The schema table describes the settings/parameters for the LLM. If the user has `display.chat.show_settings = true` then this table will be exposed at the top of the chat buffer.

We'll explore some of the options in the Copilot adapter's schema table:

```lua
schema = {
  model = {
    order = 1,
    mapping = "parameters",
    type = "enum",
    desc = "ID of the model to use. See the model endpoint compatibility table for details on which models work with the Chat API.",
    ---@type string|fun(): string
    default = "gpt-4o-2024-08-06",
    choices = {
      "gpt-4o-2024-08-06",
      "claude-3.5-sonnet",
      ["o1-preview-2024-09-12"] = { opts = { stream = false } },
      ["o1-mini-2024-09-12"] = { opts = { stream = false } },
    },
  },
}
```

The model key sets out the specific model which is to be used to interact with the Copilot endpoint. We've listed the default, in this example, as `gpt-4o-2024-08-06` but we allow the user to choose from a possible five options, via the `choices` key. We've given this an order value of `1` so that it's always displayed at the top of the chat buffer. We've also given it a useful description as this is used in the virtual text when a user hovers over it. Finally, we've specified that it has a mapping property of `parameters`. This tells the adapter that we wish to map this model key to the parameters part of the HTTP request. You'll also notice that some of the models have a table attached to them. This can be useful if you need to do conditional logic in any of the handler methods at runtime.

Let's take a look at one more schema value:

```lua
temperature = {
  order = 2,
  mapping = "parameters",
  type = "number",
  default = 0,
  condition = function(schema)
    local model = schema.model.default
    if type(model) == "function" then
      model = model()
    end
    return not vim.startswith(model, "o1")
  end,
  -- This isn't in the Copilot adapter but it's useful to reference!
  validate = function(n)
    return n >= 0 and n <= 2, "Must be between 0 and 2"
  end,
  desc = "What sampling temperature to use, between 0 and 2. Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic. We generally recommend altering this or top_p but not both.",
},
```

You'll see we've specified a function call for the `condition` key. We're simply checking that the model name doesn't being with `o1` as these models don't accept temperature as a parameter. You'll also see we've specified a function call for the `validate` key. We're simply checking that the value of the temperature is between 0 and 2


---

# Creating Prompts

The purpose of this guide is to showcase how you can extend the functionality of CodeCompanion by adding your own prompts to the config that are reflected in the _Action Palette_. The _Action Palette_ is a lua table which is parsed by the plugin and displayed as a `vim.ui.select` component. By specifying certain keys, the behaviour of the table can be customised further.

## Adding a prompt to the palette

A prompt can be added via the `setup` function:

```lua
require("codecompanion").setup({
  prompt_library = {
    ["My New Prompt"] = {
      strategy = "chat",
      description = "Some cool custom prompt you can do",
      prompts = {
        {
          role = "system",
          content = "You are an experienced developer with Lua and Neovim",
        },
        {
          role = "user",
          content = "Can you explain why ..."
        }
      },
    }
  }
})
```

In this example, if you run `:CodeCompanionActions`, you should see "My New Prompt" in the bottom of the _Prompts_ section of the palette. Clicking on your new action will initiate the _chat_ strategy and set the value of the chat buffer based on the _role_ and _content_ that's been specified in the prompt.

In the following sections, we'll explore how you can customise your prompts even more.

## Recipe #1: Creating boilerplate code

### Boilerplate HTML

As the years go by, I find myself writing less and less HTML. So when it comes to quickly scaffolding out a HTML page, I inevitably turn to a search engine. It would be great if I could have an action that could quickly generate some boilerplate HTML from the _Action Palette_.

Let's take a look at how we can achieve that:

```lua
require("codecompanion").setup({
  prompt_library = {
    ["Boilerplate HTML"] = {
      strategy = "inline",
      description = "Generate some boilerplate HTML",
      opts = {
        mapping = "<LocalLeader>ch"
      },
      prompts = {
        {
          role = "system",
          content = "You are an expert HTML programmer",
        },
        {
          role = "user",
          content = "Please generate some HTML boilerplate for me. Return the code only and no markdown codeblocks",
        },
      },
    },
  },
})
```

Nice! We've used some careful prompting to ensure that we get HTML boilerplate back from the LLM. Oh...and notice that I added a key map too!

### Leveraging pre-hooks

To make this example complete, we can leverage a pre-hook to create a new buffer and set the filetype to be html:

```lua
{
  ["Boilerplate HTML"] = {
    strategy = "inline",
    description = "Generate some boilerplate HTML",
    opts = {
      pre_hook = function()
        local bufnr = vim.api.nvim_create_buf(true, false)
        vim.api.nvim_set_current_buf(bufnr)
        vim.api.nvim_set_option_value("filetype", "html", { buf = buf } )
        return bufnr
      end
    }
    ---
  }
}
```

For the inline strategy, the plugin will detect a number being returned from the `pre_hook` and assume that is the buffer number you wish any code to be streamed into.

### Conclusion

Whilst this example was useful at demonstrating the functionality of the _Action Palette_ and your custom prompts, it's not using LLMs to add any real value to your workflow (this boilerplate could be a snippet after all!). So let's step things up in the next section.

## Recipe #2: Using context in your prompts

Now let's look at how we can use an LLM to advise us on some code that we have visually selected in a buffer. Infact, this very example used to be builtin to the plugin as the _Code Advisor_ action:

```lua
require("codecompanion").setup({
  prompt_library = {
    ["Code Expert"] = {
      strategy = "chat",
      description = "Get some special advice from an LLM",
      opts = {
        mapping = "<LocalLeader>ce",
        modes = { "v" },
        short_name = "expert",
        auto_submit = true,
        stop_context_insertion = true,
        user_prompt = true,
      },
      prompts = {
        {
          role = "system",
          content = function(context)
            return "I want you to act as a senior "
              .. context.filetype
              .. " developer. I will ask you specific questions and I want you to return concise explanations and codeblock examples."
          end,
        },
        {
          role = "user",
          content = function(context)
            local text = require("codecompanion.helpers.actions").get_code(context.start_line, context.end_line)

            return "I have the following code:\n\n```" .. context.filetype .. "\n" .. text .. "\n```\n\n"
          end,
          opts = {
            contains_code = true,
          }
        },
      },
    },
  },
})
```

At first glance there's a lot of new stuff in this. Let's break it down.

### Palette options

```lua
opts = {
  mapping = "<LocalLeader>ce",
  modes = { "v" },
  short_name = "expert",
  auto_submit = true,
  stop_context_insertion = true,
  user_prompt = true,
},
```

In the `opts` table we're specifying that we only want this action to appear in the _Action Palette_ if we're in visual mode. We're also asking the chat strategy to automatically submit the prompts to the LLM via the `auto_submit = true` value. We're also telling the picker that we want to get the user's input before we action the response with `user_prompt = true`. With the `short_name = "expert"` option, the user can run `:CodeCompanion /expert` from the cmdline in order to trigger this prompt. Finally, as we define a prompt to add any visually selected text to the chat buffer, we need to add the `stop_context_insertion = true` option to prevent the chat buffer from duplicating this. Remember that visually selecting text and opening a chat buffer will result in that selection from being adding as a codeblock.

### Prompt options and context

In the example below you can see how we've structured the prompts to get advice on the code:

```lua
prompts = {
  {
    role = "system",
    content = function(context)
      return "I want you to act as a senior "
        .. context.filetype
        .. " developer. I will ask you specific questions and I want you to return concise explanations and codeblock examples."
    end,
  },
  {
    role = "user",
    content = function(context)
      local text = require("codecompanion.helpers.actions").get_code(context.start_line, context.end_line)

      return "I have the following code:\n\n```" .. context.filetype .. "\n" .. text .. "\n```\n\n"
    end,
    opts = {
      contains_code = true,
    }
  },
},
```

One of the most useful features of the custom prompts is the ability to receive context about the current buffer and any lines of code we've selected. An example context table looks like:

```lua
{
  bufnr = 7,
  buftype = "",
  cursor_pos = { 10, 3 },
  end_col = 3,
  end_line = 10,
  filetype = "lua",
  is_normal = false,
  is_visual = true,
  lines = { "local function fire_autocmd(status)", '  vim.api.nvim_exec_autocmds("User", { pattern = "CodeCompanionInline", data = { status = status } })', "end" },
  mode = "V",
  start_col = 1,
  start_line = 8,
  winnr = 1000
}
```

Using the context above, our first prompt then makes more sense:

```lua
{
  role = "system",
  content = function(context)
    return "I want you to act as a senior "
      .. context.filetype
      .. " developer. I will ask you specific questions and I want you to return concise explanations and codeblock examples."
  end,
},
```

We are telling the LLM to act as a "senior _Lua_ developer" based on the filetype of the buffer we initiated the action from.

Lets now take a look at the second prompt:

```lua
{
  role = "user",
  content = function(context)
    local text = require("codecompanion.helpers.actions").get_code(context.start_line, context.end_line)

    return "I have the following code:\n\n```" .. context.filetype .. "\n" .. text .. "\n```\n\n"
  end,
  opts = {
    contains_code = true,
  }
},
```

You can see that we're using a handy helper to get the code between two lines and formatting it into a markdown code block.

> [!IMPORTANT]
> We've also specified a `contains_code = true` flag. If you've turned off the sending of code to LLMs then the plugin will block this from happening.

### Conditionals

It's also possible to conditionally set prompts via a `condition` function that returns a boolean:

```lua
{
  role = "user",
  ---
  condition = function(context)
    return context.is_visual
  end,
  ---
},
```

And to determine the visibility of actions in the palette itself:

```lua
{
  name = "Open chats ...",
  strategy = " ",
  description = "Your currently open chats",
  condition = function()
    return #require("codecompanion").buf_get_chat() > 0
  end,
  picker = {
    ---
  }
}
```

## Other Configuration Options

### Allowing a Prompt to appear as a Slash Command

It can be useful to have a prompt from the prompt library appear as a slash command in the chat buffer, like with the `Generate a Commit Message` action. This can be done by specifying a `is_slash_cmd = true` option to the prompt:

```lua
["Generate a Commit Message"] = {
  strategy = "chat",
  description = "Generate a commit message",
  opts = {
    index = 9,
    is_default = true,
    is_slash_cmd = true,
    short_name = "commit",
    auto_submit = true,
  },
  prompts = {
    -- Prompts go here
  }
}
```

In the chat buffer, if you type `/` you will see the value of `opts.short_name` appear in the completion menu for you to expand.

### Specifying an Adapter and Model

```lua
["Your_New_Prompt"] = {
  strategy = "chat",
  description = "Your Special Prompt",
  opts = {
    adapter = {
      name = "ollama",
      model = "deepseek-coder:6.7b",
    },
  },
  -- Your prompts here
}
```

### Specifying a Placement for Inline Prompts

As outlined in the [classification](/usage/inline-assistant.html#classification) section, an inline prompt can place its response in many different ways within a Neovim buffer. To override this, you can reference a specific placement:

```lua
["Your_New_Prompt"] = {
  strategy = "inline",
  description = "Your Special Inline Prompt",
  opts = {
    placement = "new" -- or "replace"|"add"|"before"|"chat"
  },
  -- Your prompts here
}
```

In this example, the LLM's response will be placed in a new buffer.

### Ignoring the default system prompt

It may also be useful to create custom prompts that do not send the default system prompt with the request:

```lua
["Your_New_Prompt"] = {
  strategy = "chat",
  description = "Your Special New Prompt",
  opts = {
    ignore_system_prompt = true,
  },
  -- Your prompts here
}
```

### Prompts with References

It can be useful to pre-load a chat buffer with references to _files_, _symbols_ or even _urls_. This makes conversing with an LLM that much more productive. As per `v11.9.0`, this can now be accomplished, as per the example below:

```lua
["Test References"] = {
  strategy = "chat",
  description = "Add some references",
  opts = {
    index = 11,
    is_default = true,
    is_slash_cmd = false,
    short_name = "ref",
    auto_submit = false,
  },
  -- These will appear at the top of the chat buffer
  references = {
    {
      type = "file",
      path = { -- This can be a string or a table of values
        "lua/codecompanion/health.lua",
        "lua/codecompanion/http.lua",
      },
    },
    {
      type = "file",
      path = "lua/codecompanion/schema.lua",
    },
    {
      type = "symbols",
      path = "lua/codecompanion/strategies/chat/init.lua",
    },
    {
      type = "url", -- This URL will even be cached for you!
      url = "https://raw.githubusercontent.com/olimorris/codecompanion.nvim/refs/heads/main/lua/codecompanion/commands.lua",
    },
  },
  prompts = {
    {
      role = "user",
      content = "I'll think of something clever to put here...",
      opts = {
        contains_code = true,
      },
    },
  },
},
```

## Agentic Workflows

Workflows, at their core, are simply multiple prompts which are sent to the LLM in a turn-based manner. I fully recommend reading [Issue 242](https://www.deeplearning.ai/the-batch/issue-242/) of The Batch to understand their use. Workflows are setup in exactly the same way as prompts in the prompt library. Take the `code workflow` as an example:

```lua
["Code workflow"] = {
  strategy = "workflow",
  description = "Use a workflow to guide an LLM in writing code",
  opts = {
    index = 4,
    is_default = true,
    short_name = "workflow",
  },
  prompts = {
    {
      -- We can group prompts together to make a workflow
      -- This is the first prompt in the workflow
      {
        role = constants.SYSTEM_ROLE,
        content = function(context)
          return fmt(
            "You carefully provide accurate, factual, thoughtful, nuanced answers, and are brilliant at reasoning. If you think there might not be a correct answer, you say so. Always spend a few sentences explaining background context, assumptions, and step-by-step thinking BEFORE you try to answer a question. Don't be verbose in your answers, but do provide details and examples where it might help the explanation. You are an expert software engineer for the %s language",
            context.filetype
          )
        end,
        opts = {
          visible = false,
        },
      },
      {
        role = constants.USER_ROLE,
        content = "I want you to ",
        opts = {
          auto_submit = false,
        },
      },
    },
    -- This is the second group of prompts
    {
      {
        role = constants.USER_ROLE,
        content = "Great. Now let's consider your code. I'd like you to check it carefully for correctness, style, and efficiency, and give constructive criticism for how to improve it.",
        opts = {
          auto_submit = false,
        },
      },
    },
    -- This is the final group of prompts
    {
      {
        role = constants.USER_ROLE,
        content = "Thanks. Now let's revise the code based on the feedback, without additional explanations.",
        opts = {
          auto_submit = false,
        },
      },
    },
  },
},
```

You'll notice that the comments use the notion of "groups". These are collections of prompts which are added to a chat buffer in a timely manner. Infact, the second group will only be added once the LLM has responded to the first group...and so on.

## Conclusion

Hopefully this serves as a useful introduction on how you can expand CodeCompanion to create prompts that suit your workflow. It's worth checking out [config.lua](https://github.com/olimorris/codecompanion.nvim/blob/main/lua/codecompanion/config.lua) files for more complex examples.



---

# Creating Tools

In CodeCompanion, tools offer pre-defined ways for LLMs to execute actions and act as an Agent. Tools are added to chat buffers as participants. This guide walks you through the implementation of tools, enabling you to create your own.

## Introduction

In the plugin, tools work by sharing a system prompt with an LLM. This instructs them how to produce an XML markdown code block which can, in turn, be interpreted by the plugin to execute a command or function.

The plugin has a tools class `CodeCompanion.Tools` which will call individual `CodeCompanion.Tool` such as the [cmd_runner](https://github.com/olimorris/codecompanion.nvim/blob/main/lua/codecompanion/strategies/chat/tools/cmd_runner.lua) or the [editor](https://github.com/olimorris/codecompanion.nvim/blob/main/lua/codecompanion/strategies/chat/tools/editor.lua). The calling of tools is orchestrated by the `CodeCompanion.Chat` class which parses an LLM's response and looks to identify any XML code blocks.

## Tool Types

There are two types of tools within the plugin:

1. **Command-based**: These tools can execute a series of commands in the background using a [plenary.job](https://github.com/nvim-lua/plenary.nvim/blob/master/lua/plenary/job.lua). They're non-blocking, meaning you can carry out other activities in Neovim whilst they run. Useful for heavy/time-consuming tasks.

2. **Function-based**: These tools, like the [editor](https://github.com/olimorris/codecompanion.nvim/blob/main/lua/codecompanion/strategies/chat/tools/editor.lua) one, execute Lua functions directly in Neovim within the main process.

## The Interface

Tools must implement the following interface:

```lua
---@class CodeCompanion.Tool
---@field name string The name of the tool
---@field cmds table The commands to execute
---@field schema table The schema that the LLM must use in its response to execute a tool
---@field system_prompt fun(schema: table): string The system prompt to the LLM explaining the tool and the schema
---@field opts? table The options for the tool
---@field env? fun(schema: table): table|nil Any environment variables that can be used in the *_cmd fields. Receives the parsed schema from the LLM
---@field handlers table Functions which can be called during the execution of the tool
---@field handlers.setup? fun(self: CodeCompanion.Tools): any Function used to setup the tool. Called before any commands
---@field handlers.approved? fun(self: CodeCompanion.Tools): boolean Function to call if an approval is needed before running a command
---@field handlers.on_exit? fun(self: CodeCompanion.Tools): any Function to call at the end of all of the commands
---@field output? table Functions which can be called after the command finishes
---@field output.rejected? fun(self: CodeCompanion.Tools, cmd: table): any Function to call if the user rejects running a command
---@field output.error? fun(self: CodeCompanion.Tools, cmd: table, error: table|string): any Function to call if the tool is unsuccessful
---@field output.success? fun(self: CodeCompanion.Tools, cmd: table, output: table|string): any Function to call if the tool is successful
---@field request table The request from the LLM to use the Tool
```

### `cmds`

The `cmds` table contains the list of commands or functions that will be executed by the `CodeCompanion.Tools` in succession.

**Command-Based Tools**

The `cmds` table is a collection of commands which the agent will execute one after another, asynchronously, using [plenary.job](https://github.com/nvim-lua/plenary.nvim/blob/master/lua/plenary/job.lua). It's also possible to pass in environment variables (from the `env` function) by calling them in `${}` brackets.

The now removed `code_runner` tool was setup as:

```lua
cmds = {
  { "docker", "pull", "${lang}" },
  {
    "docker",
    "run",
    "--rm",
    "-v",
    "${temp_dir}:${temp_dir}",
    "${lang}",
    "${lang}",
    "${temp_input}",
  },
}
```

In this example, the `CodeCompanion.Tools` class will call each table in order and replace the variables with output from the `env` function (more on that below).

Using the `handlers.setup()` function, it's also possible to create commands dynamically like in the `cmd_runner` tool.

**Function-based Tools**

Function-based tools use the `cmds` table to define functions that will be executed one after another:

```lua
  cmds = {
    ---@param self CodeCompanion.Tools The Tools object
    ---@param input any The output from the previous function call
    function(self, input)
      return "Hello, World"
    end,
    ---Ensure the final function returns the status and the output
    ---@param self CodeCompanion.Tools The Tools object
    ---@param input any The output from the previous function call
    ---@return { status: string, msg: string }
    function(self, input)
     print(input) -- prints "Hello, World"
    end,
  }
```

In this example, the first function will be called by the `CodeCompanion.Tools` class and its output will be captured and passed onto the final function call. It should be noted that the last function call in the `cmds` block should return a table with the status (either `success` or `error`) and a msg.

### `schema`

The schema represents the structure of the response that the LLM must follow in order to call the tool.

In the `code_runner` tool, the schema is defined as a Lua table and then converted into XML in the chat buffer:

```lua
schema = {
  name = "code_runner",
  parameters = {
    inputs = {
      lang = "python",
      code = "print('Hello World')",
    },
  },
},
```

### `env`

You can setup environment variables that other functions can access in the `env` function. This function receives the parsed schema which is requested by the LLM when it follows the schema's structure.

For the Code Runner agent, the environment was setup as:

```lua
---@param schema table
env = function(schema)
  local temp_input = vim.fn.tempname()
  local temp_dir = temp_input:match("(.*/)")
  local lang = schema.parameters.inputs.lang
  local code = schema.parameters.inputs.code

  return {
    code = code,
    lang = lang,
    temp_dir = temp_dir,
    temp_input = temp_input,
  }
end
```

Note that a table has been returned that can then be used in other functions.

### `system_prompt`

In the plugin, LLMs are given knowledge about a tool via a system prompt. This gives the LLM knowledge of the tool alongside the instructions (via the schema) required to execute it.

For the Code Runner agent, the `system_prompt` table was:

````lua
  system_prompt = function(schema)
    return string.format(
      [[### You have gained access to a new tool!

Name: Code Runner
Purpose: The tool enables you to execute any code that you've created
Why: This enables yourself and the user to validate that the code you've created is working as intended
Usage: To use this tool, you need to return an XML markdown code block (with backticks). Consider the following example which prints 'Hello World' in Python:

```xml
%s
```

You must:
- Ensure the code you're executing will be able to parsed as valid XML
- Ensure the code you're executing is safe
- Ensure the code you're executing is concise
- Ensure the code you're executing is relevant to the conversation
- Ensure the code you're executing is not malicious]],
      xml2lua.toXml(schema, "tool")
    )
````

### `handlers`

The `handlers` table consists of three methods.

The `setup` method is called before any of the `cmds` are called. This is useful if you wish to set the `cmds` dynamically on the tool itself, like in the `cmd_runner` tool.

The `approved` method, which must return a boolean, contains logic to prompt the user for their approval prior to a command being executed. This is used in both the `files` and `cmd_runner` tool to allow the user to validate the actions the LLM is proposing to take.

Finally, the `on_exit` method is called after all of the `cmds` have been executed.

### `output`

The `output` table consists of three methods.

The `rejected` method is called when a user rejects to approve the running of a command. This method is useful of informing the LLM of the rejection.

The `error` method is called to notify the LLM of an error when executing a command.

And finally, the `success` method is called to notify the LLM of a successful execution of a command.

### `request`

The request table is populated at runtime and contains the parsed XML that the LLM has requested to run.



---

# Creating Workspaces

Workspaces act as a context management system for your project. This context sits in a `codecompanion-workspace.json` file in the root of the current working directory. For the purposes of this guide, the file will be referred to as the _workspace file_.

## Structure

Below is an example workspace file for this plugin:

```json
{
  "name": "CodeCompanion.nvim",
  "version": "1.0.0",
  "workspace_spec": "1.0",
  "description": "An example workspace file",
  "system_prompt": "CodeCompanion.nvim is an AI-powered productivity tool integrated into Neovim, designed to enhance the development workflow by seamlessly interacting with various large language models (LLMs). It offers features like inline code transformations, code creation, refactoring, and supports multiple LLMs such as OpenAI, Anthropic, and Google Gemini, among others. With tools for variable management, agents, and custom workflows, CodeCompanion.nvim streamlines coding tasks and facilitates intelligent code assistance directly within the Neovim editor",
  "groups": [
    {
      "name": "Chat Buffer",
      "system_prompt": "...",
      "opts": {
        "remove_config_system_prompt": true
      },
      "files": [
        {
          "description": "...",
          "path": "..."
        }
      ],
      "symbols": [
        {
          "description": "...",
          "path": "..."
        },
      ]
    },
  ]
}
```

- The `description` value contains the high-level description of the workspace file. This is **not** sent to the LLM by default
- The `system_prompt` value contains text that will be sent to the LLM as a system prompt
- The `remove_config_system_prompt` key ensures the plugin's default system prompt (as defined in the user's config) is
removed from the chat buffer
- The `groups` array contains the grouping of files and symbols that can be shared with the LLM. In this example we just have one group, the _Chat Buffer_
- The `version` and `workspace_spec` are currently unused

> [!INFO]
> When a user selects a group to load, the workspace slash command will iterate through the group adding the description first and then sequentially adding the files and symbols. For the latter two, their description is added first, before their content.

### System Prompts

Currently, workspaces allow for system prompts to exist at the top-level of the workspace file and at a group level. The plugin will always insert top-level system prompts at the first index in the messages table in the chat buffer. Any group system prompts will be added afterwards.

## Groups

Groups are the core of the workspace file. They are where logical groupings of files and/or symbols are defined. Exploring the _Chat Buffer_ group in detail:

```json
{
  "name": "Chat Buffer",
  "system_prompt": "I've grouped a number of files together into a group I'm calling \"${group_name}\". The chat buffer is a Neovim buffer which allows a user to interact with an LLM. The buffer is formatted as Markdown with a user's content residing under a H2 header. The user types their message, saves the buffer and the plugin then uses Tree-sitter to parse the buffer, extracting the contents and sending to an adapter which connects to the user's chosen LLM. The response back from the LLM is streamed into the buffer under another H2 header. The user is then free to respond back to the LLM.\n\nBelow are the relevant files which we will be discussing:\n\n${group_files}",
  "description": "You could also add a description here which will be added as a user prompt",
  "opts": {
    "remove_config_system_prompt": true
  },
  "vars": {
    "base_dir": "lua/codecompanion/strategies/chat"
  },
  "files": [
    {
      "description": "The `${filename}` file is the entry point for the chat strategy. All methods directly relating to the chat buffer reside here.",
      "path": "${base_dir}/init.lua"
    }
  ],
  "symbols": [
    {
      "description": "References are files, buffers, symbols or URLs that are shared with an LLM to provide additional context. The `${filename}` is where this logic sits and I've shared its symbolic outline below.",
      "path": "${base_dir}/references.lua"
    },
    {
      "description": "A watcher is when a user has toggled a specific buffer to be watched. When a message is sent to the LLM by the user, any changes made to the watched buffer are also sent, giving the LLM up to date context. The `${filename}` is where this logic sits and I've shared its symbolic outline below.",
      "path": "${base_dir}/watchers.lua"
    }
  ],
  "urls": [
    {
      "ignore_cache": false,
      "description": "The plugin uses Mini.test for its testing. Below is the Mini.Test documentation:",
      "url": "https://raw.githubusercontent.com/echasnovski/mini.nvim/refs/heads/main/TESTING.md"
    },
    {
      "auto_restore_cache": true,
      "description": "I've also included a link to my README:",
      "url": "https://raw.githubusercontent.com/olimorris/codecompanion.nvim/refs/heads/main/doc/codecompanion.txt"
    }
  ],
}
```

There's a lot going on in there:

- Firstly, the `system_prompt` within the group is a way of adding to the main, workspace system prompt
- The `${group_name}` variable provides the name of the current group
- The `${group_files}` variable contains a list of all the files and symbols in the group
- The `vars` object is a way of creating variables that can be referenced throughout the files and symbols arrays
- Each object in the files/symbols array can be a string which defaults to a path, or can be an object containing a
description and the path

### Files

When _files_ are defined, their entire content is shared with the LLM alongside the description. This is useful for files where a deep understanding of how they function is required. Of course, this can consume significant tokens.

### Symbols

The plugin uses Tree-sitter [queries](https://github.com/olimorris/codecompanion.nvim/tree/main/queries) to create a symbolic outline of files, capturing:

- Classes, methods, and interfaces
- Function names
- File/library imports
- Start/end lines for each symbol

By tagging the `files` tool, the LLM can request specific line ranges from these symbols - a cost-effective alternative to sharing entire files.

### URLs

Workspace files also support the loading of data from URLs. When loading a URL, the `fetch` slash command adapter retrieves the data. The plugin:

- Caches URL data to disk by default
- Prompts before restoring from cache
- Can be configured with:
  - `"ignore_cache": true` to never use cache
  - `"auto_restore_cache": true` to always use cache without prompting

## Variables

A list of all the variables available in workspace files:

- `${workspace_description}` - The description at the top of the workspace file
- `${workspace_name}` - The name of the workspace file
- `${group_name}` - The name of the group that is being processed by the slash command
- `${group_files}` - A list of all the files and symbols in the group
- `${filename}` - The name of the current file/symbol that is being processed
- `${cwd}` - The current working directory of the workspace file
- `${path}` - The path to the current file/symbol



---
