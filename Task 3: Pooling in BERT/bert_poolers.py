import torch
import torch.nn as nn
from transformers import BertConfig
from transformers.models.bert.modeling_bert import (
    BertPreTrainedModel, BertModel,
    BertEmbeddings, BertEncoder, BertForSequenceClassification, BertPooler,
)


class MeanMaxTokensBertPooler(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.weights = nn.Linear(config.hidden_size * 2, config.hidden_size)
        self.activation = nn.Tanh()

    def forward(self, hidden_states, *args, **kwargs):
        hidden_mean = torch.sum(hidden_states, 1) / hidden_states.size(1)
        hidden_max, _ = torch.max(hidden_states, 1)
        mean_max_tokens = torch.cat((hidden_mean, hidden_max), 1)
        pooled = self.weights(mean_max_tokens)
        pooled = self.activation(pooled)
        return pooled


# TopKMeanBertPooler
class MyBertPooler(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.weights = nn.Linear(config.hidden_size, config.hidden_size)
        self.activation = nn.Tanh()

    def forward(self, hidden_states, *args, **kwargs):
        k = 20  # 10, 20, 30, hidden_states.shape[1] // 2
        top_k, _ = torch.topk(hidden_states, k, dim=1)
        top_k_mean = torch.sum(top_k, 1) / top_k.size(1)
        pooled = self.weights(top_k_mean)
        pooled = self.activation(pooled)
        return pooled


class MyBertConfig(BertConfig):
    def __init__(self, pooling_layer_type="CLS", **kwargs):
        super().__init__(**kwargs)
        self.pooling_layer_type = pooling_layer_type


class MyBertModel(BertModel):

    def __init__(self, config: MyBertConfig):
        super(BertModel, self).__init__(config)
        self.config = config

        self.embeddings = BertEmbeddings(config)
        self.encoder = BertEncoder(config)

        if config.pooling_layer_type == "CLS":
            # See src/transformers/models/bert/modeling_bert.py#L610
            # at huggingface/transformers (9f43a425fe89cfc0e9b9aa7abd7dd44bcaccd79a)
            self.pooler = BertPooler(config)
        elif config.pooling_layer_type == "MEAN_MAX":
            self.pooler = MeanMaxTokensBertPooler(config)
        elif config.pooling_layer_type == "TOPK_MEAN":
            self.pooler = TopKMeanBertPooler(config)
        elif config.pooling_layer_type == "TOPHALF_MEAN":
            self.pooler = TopHalfMeanBertPooler(config)
        elif config.pooling_layer_type == "MEAN_CLS":
            self.pooler = MeanCLSBertPooler(config)
        elif config.pooling_layer_type == "TOPK_MEAN_CLS":
            self.pooler = TopKMeanCLSBertPooler(config)
        
        else:
            raise ValueError(f"Wrong pooling_layer_type: {config.pooling_layer_type}")

        self.init_weights()

    @property
    def pooling_layer_type(self):
        return self.config.pooling_layer_type


class MyBertForSequenceClassification(BertForSequenceClassification):
    def __init__(self, config):
        super(BertForSequenceClassification, self).__init__(config)
        self.num_labels = config.num_labels

        self.bert = MyBertModel(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, config.num_labels)

        self.init_weights()

    def forward(
            self,
            input_ids=None,
            attention_mask=None,
            token_type_ids=None,
            position_ids=None,
            head_mask=None,
            inputs_embeds=None,
            labels=None,
            output_attentions=None,
            output_hidden_states=None,
            return_dict=None,
    ):
        return super().forward(
            input_ids, attention_mask, token_type_ids, position_ids, head_mask,
            inputs_embeds, labels, output_attentions, output_hidden_states, return_dict
        )
        