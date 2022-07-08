import os
import datetime
import importlib
import random
import torch
import numpy as np
import time
from typing import Union
from transformers import AutoTokenizer
from .enum_type import PLM_MODELS


class Timer:

    def __enter__(self):
        self.__stime = time.time()
        return self

    def __exit__(self, *exc_info):
        self.__etime = time.time()

    @property
    def duration(self) -> float:
        return self.__etime - self.__stime


def get_local_time() -> str:
    r"""Get current time

    Returns:
        str: current time
    """
    cur = datetime.datetime.now()
    cur = cur.strftime('%Y-%b-%d_%H-%M-%S')

    return cur


def ensure_dir(dir_path: str):
    r"""Make sure the directory exists, if it does not exist, create it

    Args:
        dir_path (str): directory path

    """
    os.makedirs(dir_path, exist_ok=True)


def ordinal(n: Union[str, int]) -> str:
    """convert into ordinal number string"""
    n = int(n)
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
    return str(n) + suffix


def get_model(model_name):
    r"""Automatically select model class based on model name

    Args:
        model_name (str): model name

    Returns:
        Generator: model class
    """
    try:
        model_name = 'Pretrained_Models' if model_name.lower() in PLM_MODELS else model_name
        model_file_name = model_name.lower()
        module_path = '.'.join(['...model', model_file_name])
        if importlib.util.find_spec(module_path, __name__):
            model_module = importlib.import_module(module_path, __name__)
        model_class = getattr(model_module, model_name)
    except:
        raise NotImplementedError("{} can't be found".format(model_name))
    return model_class


def get_trainer(model_name):
    r"""Automatically select trainer class based on model type and model name

    Args:
        model_name (str): model name

    Returns:
        ~textbox.trainer.trainer.Trainer: trainer class
    """
    try:
        return getattr(importlib.import_module('textbox.trainer.trainer'), model_name + 'Trainer')
    except AttributeError:
        return getattr(importlib.import_module('textbox.trainer.trainer'), 'Trainer')

def get_tokenizer(config):
    model_name = config['model_name']
    if model_name in PLM_MODELS:
        tokenizer_kwargs = config['tokenizer_kwargs'] or {}
        tokenizer_path = config['tokenizer_path'] or config['model_path']
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, **tokenizer_kwargs)

        # (1): tokenizer needs to add eos token
        if model_name in ['ctrl', 'openai-gpt']:
            tokenizer.add_special_tokens(({'eos_token': '</s>'}))

        # (2): tokenizer needs to add pad token
        if model_name in ['ctrl', 'gpt2', 'gpt_neo', 'openai-gpt']:
            tokenizer.pad_token = tokenizer.eos_token
        
        # (3): tokenizer needs to change replace eos token with sep token
        if model_name in ['cpm']:
            tokenizer.eos_token = tokenizer.sep_token

        # (4): tokenizer needs to modify `build_inputs_with_special_tokens()` and `num_special_tokens_to_add()`
        if model_name in ['blenderbot-small', 'cpm', 'ctrl', 'gpt2', 'gpt_neo', 'openai-gpt']:
            tokenizer.build_inputs_with_special_tokens = lambda t0, t1=None: t0 + [tokenizer.eos_token_id]
            tokenizer.num_special_tokens_to_add = lambda : 1
        elif model_name in ['opt']:
            tokenizer.build_inputs_with_special_tokens = lambda t0, t1=None: [tokenizer.bos_token_id] + t0 + [tokenizer.eos_token_id]
            tokenizer.num_special_tokens_to_add = lambda : 2

        # (5): tokenizer needs to set src_lang, tgt_lang (used in translation task)
        if model_name in ['m2m_100', 'mbart']:
            assert config['src_lang'] and config['tgt_lang'], \
                model_name + ' needs to specify source language and target language with `--src_lang=xx` and `--tgt_lang=xx`'
            tokenizer.src_lang = config['src_lang']
            tokenizer.tgt_lang = config['tgt_lang']
    
    return tokenizer

def init_seed(seed, reproducibility):
    r""" init random seed for random functions in numpy, torch, cuda and cudnn

    Args:
        seed (int): random seed
        reproducibility (bool): Whether to require reproducibility
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if reproducibility:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    else:
        torch.backends.cudnn.benchmark = True
        torch.backends.cudnn.deterministic = False
