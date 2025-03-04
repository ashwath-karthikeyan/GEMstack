import yaml
import os
import os.path as osp
import glob
import numpy as np
from easydict import EasyDict
from .utils import recreate_dirs


class Config:

    def __init__(self, config_path, tmp=False, create_dirs=False):
        self.yml_dict = EasyDict(yaml.safe_load(open(config_path, 'r')))
        # data dir
        self.results_root_dir = os.path.expanduser(self.yml_dict['results_root_dir'])
        # results dirs
        cfg_root_dir = '/tmp/agentformer' if tmp else self.results_root_dir
        self.cfg_root_dir = os.path.expanduser(cfg_root_dir)

        self.cfg_dir = '%s/%s' % (self.cfg_root_dir, 'inference')
        self.result_dir = '%s/results' % self.cfg_dir
        self.log_dir = '%s/log' % self.cfg_dir
        self.tb_dir = '%s/tb' % self.cfg_dir
        self.model_path = self.yml_dict['model_path']
        if create_dirs:
            recreate_dirs(self.tb_dir)

    def get_last_epoch(self):
        model_files = sorted(glob.glob(os.path.join(self.model_dir, 'model_*.p')))
        if len(model_files) == 0:
            return None
        else:
            model_file = osp.basename(model_files[-1])
            epoch = int(osp.splitext(model_file)[0].split('model_')[-1])
            return epoch            

    def __getattribute__(self, name):
        yml_dict = super().__getattribute__('yml_dict')
        if name in yml_dict:
            return yml_dict[name]
        else:
            return super().__getattribute__(name)

    def __setattr__(self, name, value):
        try:
            yml_dict = super().__getattribute__('yml_dict')
        except AttributeError:
            return super().__setattr__(name, value)
        if name in yml_dict:
            yml_dict[name] = value
        else:
            return super().__setattr__(name, value)

    def get(self, name, default=None):
        if hasattr(self, name):
            return getattr(self, name)
        else:
            return default
            